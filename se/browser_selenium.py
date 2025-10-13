# Copyright 2025 Laurent Defert
#
#  This file is part of Sosse.
#
# Sosse is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Sosse is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with Sosse.
# If not, see <https://www.gnu.org/licenses/>.

import json
import logging
import os
import re
import shlex
from datetime import datetime
from io import BytesIO
from time import sleep

import psutil
import pytz
from django.conf import settings
from PIL import Image

from .browser import (
    AuthElemFailed,
    Browser,
    PageTooBig,
    StalledDownload,
    TooManyRedirects,
    retry,
)
from .browser_request import BrowserRequest
from .cookie import Cookie
from .page import NAV_ELEMENTS, Page
from .url import has_browsable_scheme, sanitize_url, urlparse

crawl_logger = logging.getLogger("crawler")


class BrowserSelenium(Browser):
    _worker_no = 0
    _driver = None
    cookie_loaded = []
    COOKIE_LOADED_SIZE = 1024
    first_init = True
    CONTENT_HANDLERS = tuple()

    @classmethod
    def driver(cls):
        cls.init()
        return cls._driver

    @classmethod
    def _init(cls):
        from .browser_chromium import BrowserChromium
        from .browser_firefox import BrowserFirefox

        if not os.path.isdir(BrowserChromium._get_download_dir()):
            os.makedirs(BrowserChromium._get_download_dir())
        if not os.path.isdir(BrowserFirefox._get_download_dir()):
            os.makedirs(BrowserFirefox._get_download_dir())

        # force the cwd in case it's not called from the worker
        if not os.getcwd().startswith(settings.SOSSE_TMP_DL_DIR + "/"):
            # change cwd to Chromium's because it downloads directory (while Firefox has an option for target dir)
            os.chdir(BrowserChromium._get_download_dir())

        # Force HOME directory as it used for Firefox profile loading
        os.environ["HOME"] = "/var/www"

        config_dir = settings.SOSSE_BROWSER_CONFIG_DIR
        os.environ["XDG_CONFIG_HOME"] = config_dir

        opt_key = f"SOSSE_{cls.name.upper()}_OPTIONS"
        opts = shlex.split(getattr(settings, opt_key))
        w, h = cls.screen_size()
        opts.append(f"--window-size={w},{h}")
        opts += cls._get_options()

        has_incognito = False
        options = cls._get_options_obj()
        for opt in opts:
            if cls.first_init:
                crawl_logger.info(f"Passing option {opt}")
            options.add_argument(opt)

            if "--incognito" in opt:
                has_incognito = True

        if cls.first_init and has_incognito:
            crawl_logger.warning("Passing --incognito breaks file downloads on some versions of Chromium")

        cls.first_init = False
        cls._driver = cls._get_driver(options)
        cls._driver.delete_all_cookies()

    @classmethod
    def _destroy(cls):
        if cls._driver:
            # Ignore errors in case the browser crashed
            try:
                cls._driver.close()
            except:  # noqa # nosec B110
                pass

            try:
                cls._driver.quit()
            except:  # noqa # nosec B110
                pass

    @classmethod
    def _current_url(cls):
        if cls.driver().current_url.startswith("data:"):
            return ""
        return sanitize_url(cls.driver().current_url)

    @classmethod
    def _driver_get(cls, url, force_reload=False):
        raise NotImplementedError()

    @classmethod
    def _wait_for_ready(cls, url):
        crawl_logger.debug(
            f"wait_for_ready {url}, {settings.SOSSE_MAX_REDIRECTS} / {settings.SOSSE_JS_STABLE_RETRY} / {settings.SOSSE_JS_STABLE_TIME}",
        )
        redirect_count = 0

        retry = settings.SOSSE_JS_STABLE_RETRY
        while redirect_count <= settings.SOSSE_MAX_REDIRECTS:
            # Wait for page being ready
            while retry > 0 and cls._current_url() == url:
                retry -= 1
                if cls.driver().execute_script('return document.readyState === "complete";'):
                    break
                sleep(settings.SOSSE_JS_STABLE_TIME)

            new_url = cls._current_url()
            if new_url != url:
                crawl_logger.debug(f"detected redirect {redirect_count} {url} -> {new_url}")
                redirect_count += 1
                url = new_url
                continue

            crawl_logger.debug(f"js stabilization start {url}")

            # Inject DOM observer to track changes
            cls.driver().execute_script("""
                document.sosseReady = true;
                document.sosseObserver = new MutationObserver(() => {
                    document.sosseReady = false;
                });
                document.sosseObserver.observe(document.body, {
                    childList: true,
                    subtree: true,
                    attributes: true,
                    characterData: true
                });
            """)

            while retry > 0 and cls._current_url() == url:
                sleep(settings.SOSSE_JS_STABLE_TIME)
                retry -= 1

                is_ready = cls.driver().execute_script("return document.sosseReady;")
                if is_ready:
                    break
                else:
                    cls.driver().execute_script("document.sosseReady = true;")
                    crawl_logger.debug(f"js changed {url}")

            # Clean up observer
            cls.driver().execute_script("""
                if (document.sosseObserver) {
                    document.sosseObserver.disconnect();
                    delete document.sosseObserver;
                    delete document.sosseReady;
                }
            """)

            if cls._current_url() != url:
                redirect_count += 1
                url = cls._current_url()
                continue
            else:
                crawl_logger.debug(f"js stable {url}")
                break

        if redirect_count > settings.SOSSE_MAX_REDIRECTS:
            raise TooManyRedirects()

        return redirect_count

    @classmethod
    def remove_nav_elements(cls):
        nav_elements = json.dumps(NAV_ELEMENTS)
        cls.driver().execute_script(
            f"""
        const tags = {nav_elements};
        tags.map((tag) => {{
            const elems = document.getElementsByTagName(tag);
            for (no = 0; no < elems.length; no++) {{
                elems[no].remove();
            }}
        }});
        """
        )

    @classmethod
    def _escape_content_handler(cls, content):
        content_url = None
        for content_re in cls.CONTENT_HANDLERS:
            m = re.match(content_re, content)
            if m:
                content_url = m.group("url").decode("utf-8")
                page = BrowserRequest.get(content_url, None)
                return page.content
        return content

    @classmethod
    def _get_page(cls, url, collection):
        redirect_count = cls._wait_for_ready(url)

        current_url = cls.driver().current_url
        script_result = None
        if collection and collection.script:
            script_result = cls.driver().execute_script(collection.script)
            cls._wait_for_ready(url)

        content = cls.driver().page_source.encode("utf-8")
        content = cls._escape_content_handler(content)
        page = Page(current_url, content, cls, script_result=script_result)
        page.title = cls.driver().title
        page.redirect_count = redirect_count
        return page

    @classmethod
    def _save_cookies(cls, url):
        _cookies = []
        crawl_logger.debug(f"got cookies {cls.driver().get_cookies()}")
        for cookie in cls.driver().get_cookies():
            c = {
                "name": cookie["name"],
                "value": cookie["value"],
                "path": cookie["path"],
                "secure": cookie["secure"],
            }

            expires = cookie.get("expiry")
            if expires:
                c["expires"] = datetime.fromtimestamp(expires, pytz.utc)

            if cookie.get("sameSite"):
                if cookie["sameSite"] == "None":
                    # Firefox returns "None" since v140, when SameSite is not set
                    # We force to "Lax" to align with Chromium
                    c["same_site"] = "Lax"
                else:
                    c["same_site"] = cookie["sameSite"]

            if cookie.get("httpOnly"):
                c["http_only"] = cookie["httpOnly"]

            if cookie.get("domain"):
                c["domain"] = cookie["domain"]

            _cookies.append(c)

        Cookie.set(url, _cookies)

    @classmethod
    def _load_cookies(cls, url):
        if not has_browsable_scheme(url):
            return

        # Cookies can only be set to the same domain,
        # so first we navigate to the correct location
        current_url = urlparse(cls._current_url())
        dest = sanitize_url(url)
        target_url = urlparse(dest)
        cookies = Cookie.get_from_url(dest)
        if len(cookies) == 0:
            crawl_logger.debug(f"no cookie to load for {dest}")
            return

        if current_url.netloc != target_url.netloc:
            crawl_logger.debug(f"navigate for cookie to {dest}")
            cls._driver_get(dest)
            cls._wait_for_ready(dest)
            crawl_logger.debug(f"navigate for cookie done {cls._current_url()}")

        current_url = cls._current_url()
        if urlparse(current_url).netloc != target_url.netloc:
            # if the browser is initially on about:blank,
            # and then loads a download url, it'll stay on about:blank
            # which does not accept cookie loading
            crawl_logger.debug(
                f"could not go to {target_url.netloc} to load cookies, nav is stuck on {current_url} ({cls.driver().current_url})",
            )
            return

        crawl_logger.debug("clearing cookies")
        cls.driver().delete_all_cookies()
        for c in cookies:
            cookie = {
                "name": c.name,
                "value": c.value,
                "path": c.path,
                "secure": c.secure,
                "sameSite": c.same_site.title(),
            }
            if c.domain_cc:
                cookie["domain"] = c.domain_cc
            if c.expires:
                cookie["expiry"] = int(c.expires.strftime("%s"))
            if c.http_only:
                cookie["httpOnly"] = c.http_only
            try:
                cls.driver().add_cookie(cookie)
                crawl_logger.debug(f"loaded cookie {cookie}")
            except:  # noqa
                raise Exception(f"{cookie}\n{cls.driver().current_url}")

    @classmethod
    @retry
    def get(cls, url, collection):
        current_url = cls.driver().current_url
        crawl_logger.debug(f"get on {url}, current {current_url}")

        # Clear the download dir
        crawl_logger.debug(f"clearing {cls._get_download_dir()}")
        for f in os.listdir(cls._get_download_dir()):
            f = os.path.join(cls._get_download_dir(), f)
            if os.path.isfile(f):
                crawl_logger.warning(
                    f'Deleting stale download file {f} (you may fix the issue by adjusting "dl_check_*" variables in the conf)'
                )
                os.unlink(f)

        crawl_logger.debug("loading cookies")
        cls._load_cookies(url)
        crawl_logger.debug("driver get")

        # Force reload to use the new cookies
        cls._driver_get(url, force_reload=True)

        if (
            (
                current_url != url and cls.driver().current_url == current_url
            )  # If we got redirected to the url that was previously set in the browser
            or cls.driver().current_url == "data:,"
        ):  # The url can be "data:," during a few milliseconds when the download starts
            crawl_logger.debug(f"download starting ({cls.driver().current_url})")
            page = cls._handle_download(url)
            if page:
                return page

        crawl_logger.debug("page get")
        page = cls._get_page(url, collection)
        crawl_logger.debug("save cookies")
        cls._save_cookies(url)
        return page

    @classmethod
    def _handle_download(cls, url):
        retry = settings.SOSSE_DL_CHECK_RETRY
        filename = None
        while retry:
            filename = cls._get_download_file()
            if filename is not None:
                try:
                    if os.stat(filename).st_size != 0:
                        # Firefox first create an empty file, then renames it to download into it
                        break
                except FileNotFoundError:
                    sleep(settings.SOSSE_DL_CHECK_TIME)
                    retry -= 1
                    continue

            crawl_logger.debug(f"no download in progress ({filename})")
            sleep(settings.SOSSE_DL_CHECK_TIME)
            retry -= 1
        else:
            # redo the check in case SOSSE_DL_CHECK_RETRY == 0
            filename = cls._get_download_file()

        if filename is None:
            crawl_logger.debug(f"no download has started on {url}")
            return

        crawl_logger.debug(f"Download in progress: {os.listdir(cls._get_download_dir())}")
        crawl_logger.debug(f"Download file: {filename}")
        try:
            _size = None
            retry = settings.SOSSE_DL_CHECK_RETRY
            while True:
                sleep(settings.SOSSE_DL_CHECK_TIME)
                size = os.stat(filename).st_size
                if _size == size:
                    retry -= 1
                    if retry <= 0:
                        raise StalledDownload()
                else:
                    retry = settings.SOSSE_DL_CHECK_RETRY

                if size / 1024 > settings.SOSSE_MAX_FILE_SIZE:
                    cls.destroy()  # cancel the download
                    raise PageTooBig(size, settings.SOSSE_MAX_FILE_SIZE)

                if not cls._download_in_progress(filename):
                    break
        except FileNotFoundError:
            # when the download is finished the file is renamed
            pass

        crawl_logger.debug(f"Download done: {os.listdir(cls._get_download_dir())}")

        filename = cls._get_download_file()
        size = os.stat(filename).st_size
        if size / 1024 > settings.SOSSE_MAX_FILE_SIZE:
            raise PageTooBig(size, settings.SOSSE_MAX_FILE_SIZE)
        with open(filename, "rb") as f:
            content = f.read()

        page = Page(url, content, cls)

        # Remove all files in case multiple were downloaded
        for f in os.listdir(cls._get_download_dir()):
            f = os.path.join(cls._get_download_dir(), f)
            if os.path.isfile(f):
                os.unlink(f)
        return page

    @classmethod
    def screen_size(cls):
        w, h = settings.SOSSE_SCREENSHOTS_SIZE.split("x")
        return int(w), int(h)

    @classmethod
    @retry
    def create_thumbnail(cls, url, image_name):
        cls.driver().set_window_rect(0, 0, *cls.screen_size())
        cls.driver().execute_script('document.body.style.overflow = "hidden"')

        base_name = os.path.join(settings.SOSSE_THUMBNAILS_DIR, image_name)
        dir_name = os.path.dirname(base_name)
        os.makedirs(dir_name, exist_ok=True)
        thumb_png = base_name + ".png"
        thumb_jpg = base_name + ".jpg"

        try:
            cls.driver().get_screenshot_as_file(thumb_png)
            with Image.open(thumb_png) as img:
                img = img.convert("RGB")  # Remove alpha channel from the png
                img.thumbnail((160, 100))
                img.save(thumb_jpg, "jpeg")
        finally:
            if os.path.exists(thumb_png):
                os.unlink(thumb_png)

    @classmethod
    @retry
    def take_screenshots(cls, collection, image_name):
        from .collection import Collection

        if collection and collection.remove_nav_elements in (
            Collection.REMOVE_NAV_FROM_SCREENSHOT,
            Collection.REMOVE_NAV_FROM_ALL,
        ):
            cls.remove_nav_elements()

        base_name = os.path.join(settings.SOSSE_SCREENSHOTS_DIR, image_name)
        dir_name = os.path.dirname(base_name)
        os.makedirs(dir_name, exist_ok=True)

        screen_width, screen_height = cls.screen_size()
        cls.driver().set_window_rect(0, 0, screen_width, screen_height)
        cls.driver().execute_script('document.body.style.overflow = "hidden"')
        doc_height = cls.driver().execute_script(
            """
            window.scroll(0, 0);
            const body = document.body;
            const html = document.documentElement;
            return Math.max(body.scrollHeight, body.offsetHeight,
                            html.clientHeight, html.scrollHeight, html.offsetHeight);
            """
        )

        img_no = 0
        top_offset = 0
        remainging_height = doc_height
        while remainging_height > 0:
            missing_height = cls.scroll_to_page(top_offset)
            crawl_logger.debug(f"Scrolling to {top_offset} (missing {missing_height} / {remainging_height})")
            screenshot_file = f"{base_name}_{img_no}.png"
            screenshot = cls.driver().get_screenshot_as_png()

            # Compute the height of the image, this is required because
            # the size of the viewport is different from the size of the window
            img = Image.open(BytesIO(screenshot))
            img_width, img_height = img.size

            top_offset += img_height
            remainging_height -= img_height
            img_no += 1

            # For the last screenshot, we cannot scroll past the bottom
            # of the page, so we need to remove extra content from the screenshot
            if missing_height > 0 and missing_height < img_height:
                cropped_img = img.crop((0, missing_height, img_width, img_height))
                cropped_img.save(screenshot_file, "PNG")
            else:
                with open(screenshot_file, "wb") as f:
                    f.write(screenshot)

        return img_no

    @classmethod
    def scroll_to_page(cls, height):
        return int(
            cls.driver().execute_script(
                f"""
            // scroll the main window
            window.scroll(0, {height});

            // scroll other element that have a scroll (like navigation tab)
            [...document.querySelectorAll('*')].filter(x => x.clientHeight < x.scrollHeight).forEach(e => {{
                e.scroll({{left: 0, top: {height}, behavior: 'instant'}});
            }});
            return {height} - document.documentElement.scrollTop;
            """
            )
        )

    @classmethod
    def get_link_pos_abs(cls, selector):
        return cls.driver().execute_script(
            f"""
            const e = document.evaluate('{selector}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);

            if (e === null) {{
                return {{}}
            }};
            let el = e.singleNodeValue;
            if (el === null) {{
                return {{}}
            }};
            if (el.children.length === 1 && el.children[0].tagName === 'IMG') {{
                el = el.children[0];
            }}
            const bodyRect = document.body.getBoundingClientRect();
            const elemRect = el.getBoundingClientRect();
            const pageWidth = {cls.screen_size()[0]};
            if (elemRect.left >= pageWidth) {{
                return {{}};
            }}
            return {{
                elemLeft: elemRect.left,
                elemTop: elemRect.top,
                elemRight: Math.min(pageWidth, elemRect.right),
                elemBottom: elemRect.bottom,
            }}
        """
        )

    @classmethod
    def _find_elements_by_selector(cls, obj, selector):
        if hasattr(obj, "find_elements_by_css_selector"):
            return obj.find_elements_by_css_selector(selector)

        # Selenium 4
        from selenium.webdriver.common.by import By

        return obj.find_elements(By.CSS_SELECTOR, selector)

    @classmethod
    @retry
    def try_auth(cls, page, url, collection):
        form = cls._find_elements_by_selector(cls.driver(), collection.auth_form_selector)

        if len(form) == 0:
            raise AuthElemFailed(
                page,
                f"Could not find auth element with CSS selector: {collection.auth_form_selector}",
            )

        if len(form) > 1:
            raise AuthElemFailed(
                page,
                f"Found multiple auth element with CSS selector: {collection.auth_form_selector}",
            )

        crawl_logger.debug("form found")
        form = form[0]
        for f in collection.authfield_set.values("key", "value"):
            elem = cls._find_elements_by_selector(form, f'input[name="{f["key"]}"]')
            if len(elem) != 1:
                raise Exception(f"Found {len(elem)} input element when trying to set auth field {f['key']}")
            elem[0].send_keys(f["value"])
            crawl_logger.debug(f"settings {f['key']} = {f['value']} on {elem[0]}")

        dl_dir_files = cls.page_change_wait_setup()
        form.submit()
        crawl_logger.debug("submitting")
        cls.page_change_wait(dl_dir_files)

        current_url = cls._current_url()
        crawl_logger.debug(f"ready after submit {current_url}")
        cls._save_cookies(current_url)

        if current_url != url:
            return cls.get(url, collection)

        return cls._get_page(url, collection)

    @classmethod
    def page_change_wait_setup(cls):
        dl_dir_files = sorted(os.listdir(cls._get_download_dir()))
        crawl_logger.debug(f"dl_dir state: {dl_dir_files}")

        # Work-around to https://github.com/SeleniumHQ/selenium/issues/4769
        # When a download starts, the regular cls.driver().get call is stuck
        cls.driver().execute_script(
            """
            window.sosseUrlChanging = true;
            addEventListener('readystatechange', () => {
                window.sosseUrlChanging = false;
            });
        """
        )
        return dl_dir_files

    @classmethod
    def page_change_wait(cls, dl_dir_files):
        retry = settings.SOSSE_JS_STABLE_RETRY
        while (
            cls.driver().current_url == "about:blank" or cls.driver().execute_script("return window.sosseUrlChanging")
        ) and retry > 0:
            crawl_logger.debug(f"driver get not done: {cls.driver().current_url}")
            if dl_dir_files != sorted(os.listdir(cls._get_download_dir())):
                return
            sleep(settings.SOSSE_JS_STABLE_TIME)
            retry -= 1

    @classmethod
    def _download_in_progress(cls, filename):
        gecko_pid = cls._driver.service.process.pid
        p = psutil.Process(gecko_pid)
        pid = p.children()[0].pid
        fd_dir = f"/proc/{pid}/fd/"

        for f in os.listdir(fd_dir):
            f = os.path.join(fd_dir, f)
            try:
                if os.readlink(f) == filename:
                    return True
            except FileNotFoundError:
                pass
        return False
