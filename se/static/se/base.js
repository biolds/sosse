function getLang() {
  if (localStorage.getItem('sosseLanguage')) {
    return localStorage.getItem('sosseLanguage');
  } else {
    return (navigator.language || navigator.userLanguage).replace(/-.*/, '');
  }
}

function getCachedLinks() {
  if (localStorage.getItem('sosseCachedLinks') === 'true') {
    return true;
  } else {
    return false;
  }
}

function getPageSize(defaultPageSize) {
  if (localStorage.getItem('sossePageSize')) {
    return parseInt(localStorage.getItem('sossePageSize'));
  } else {
    if (!defaultPageSize) {
        console.error('defaultPageSize is null');
    }
    return defaultPageSize;
  }
}

document.addEventListener("DOMContentLoaded", function(event) {
    // Panel opening on menu buttons
    const buttons = document.getElementsByClassName('menu_button');
    for (let i = 0; i < buttons.length; i++) {
        const el = buttons[i];
        el.addEventListener('click', function(ev) {
            const panel = ev.target.parentElement.getElementsByClassName('panel')[0];
            const panelDisplayed = panel.style.display === 'block';
            panel.style.display = panelDisplayed ? 'none': 'block';
        }, false);
    }

    if (document.getElementById('search_form')) {
        const langInput = document.getElementById('id_l');
        langInput.value = getLang();

        if (localStorage.getItem('sossePageSize')) {
          const pageSize = document.getElementById('id_ps');
          pageSize.value = getPageSize();
        }

        const cachedLinks = document.getElementById('id_c');
        if (getCachedLinks()) {
            cachedLinks.value = '1';
        } else {
            document.getElementById('search_field').removeChild(cachedLinks);
        }

        const search_field = document.getElementById('search_field');
        const search_button = document.getElementById('search_button');
        const search_input = document.getElementById('id_q');
        const clear = document.createElement('input');
        clear.id = 'clear_button';
        clear.className = 'img_button';
        clear.setAttribute('type', 'button');
        clear.setAttribute('value', ' ');
        clear.addEventListener('click', function(ev) {
            search_input.focus();
            search_input.value = '';
        });
        if (window.location.pathname !== '/') {
            clear.style = 'height: 31px; width: 31px; padding-top: 6px; padding-block: 1px; border-left-style: none';
            search_input.style = 'height: 7px; min-height: 7px; border-right-style: none';
        } else {
            search_input.style = 'border-right-style: none';
        }
        search_field.insertBefore(clear, search_button);
    }
});

// Close menu panels on click outside
// https://www.w3docs.com/snippets/javascript/how-to-detect-a-click-outside-an-element.html
document.addEventListener("click", (evt) => {
    const panels = document.getElementsByClassName('panel');
    for (let i = 0; i < panels.length; i++) {
        const panel = panels[i];

        if (panel.style.display === 'none') {
            continue;
        }

        let targetEl = evt.target;
        let needHide = true;
        const button = panel.parentElement.getElementsByClassName('menu_button')[0];

        while (targetEl) {
            if(targetEl === button) {
                needHide = false;
                break
            }
            targetEl = targetEl.parentNode;
        }
        if (needHide) {
            panel.style.display = 'none';
        }
    }
});
