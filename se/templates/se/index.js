window.onload = function() {
    const langInput = document.getElementById('id_l');
    langInput.value = getLang();

    const pageSize = document.getElementById('id_ps');
    pageSize.value = getPageSize();

    load_adv_search();

    const form = document.getElementById('search_form');
    form.addEventListener('submit', on_submit, false);
}

let adv_search_lines = 0;

function search_more() {
    const more_link = document.getElementById('more');
    more_link.innerText = '- less';
    more_link.setAttribute('onclick', 'search_less()');
    const q = document.getElementById('id_q');
    q.removeAttribute('required');

    if (adv_search_lines === 0) {
        add_new_adv_search()
    }
    const adv_search = document.getElementById('adv_search');
    adv_search.removeAttribute('style');

    return false;
}

function search_less() {
    const more_link = document.getElementById('more');
    more_link.innerText = '+ more';
    more_link.setAttribute('onclick', 'search_more()');
    const q = document.getElementById('id_q');
    q.setAttribute('required' ,'');

    const adv_search = document.getElementById('adv_search');
    adv_search.style.display = 'none';

    return false;

}

function add_new_adv_search() {
    adv_search_lines++;

    const adv_search = document.getElementById('adv_search');
    const template = document.getElementById('adv_search_tmpl');

    new_adv_search = document.createElement('div');
    new_adv_search.setAttribute('id', 'adv_search' + adv_search_lines);
    new_adv_search.innerHTML = template.innerHTML;
    new_adv_search.className = 'adv_search';
    for (let i = 0; i < new_adv_search.children.length; i++) {
        const child = new_adv_search.children[i];
        if (['INPUT', 'SELECT'].indexOf(child.tagName) === -1) {
            continue;
        }
        if (!child.getAttribute('name')) {
            continue;
        }
        const name = child.getAttribute('name');
        child.setAttribute('name', name + adv_search_lines);
    }

    const dyn_buttons = new_adv_search.getElementsByClassName('dyn_button');
    for (let i = 0; i < dyn_buttons.length; i++) {
        const button = dyn_buttons[i];
        if (button.getAttribute('value') === '+') {
            button.setAttribute('onclick', 'add_new_adv_search()');
        }
        if (button.getAttribute('value') === '-') {
            if (adv_search_lines === 1) {
                button.style.display = 'none';
            } else {
                button.setAttribute('onclick', `del_adv_search(${adv_search_lines})`);
            }
        }
    }

    if (adv_search.children.length > 1) {
        const adv_search_children = adv_search.children;
        const prev_add = adv_search_children[adv_search_children.length - 1];
        const prev_dyn_buttons = prev_add.getElementsByClassName('dyn_button');
        for (let i = 0; i < prev_dyn_buttons.length; i++) {
            const button = prev_dyn_buttons[i];
            if (button.getAttribute('value') === '+') {
                button.style.display = 'none';
            }
        }
    }

    adv_search.appendChild(new_adv_search);
}

function del_adv_search(no) {
    const adv_search = document.getElementById('adv_search');
    const to_del = document.getElementById('adv_search' + no);

    const adv_search_children = adv_search.children;
    if (adv_search_children[adv_search_children.length - 1] === to_del && adv_search_children.length > 2) {
        const minus = adv_search_children[adv_search_children.length - 2];
        const buttons = minus.getElementsByClassName('dyn_button');
        for (let i = 0; i < buttons.length; i++) {
            if (buttons[i].getAttribute('value') === '+') {
                buttons[i].removeAttribute('style');
                break;
            }
        }
    }
    to_del.remove()
}

function load_adv_search() {
    // Parse url params
    // https://stackoverflow.com/questions/8486099/how-do-i-parse-a-url-query-parameters-in-javascript
    if (!location.search) {
        return;
    }

    const paramsString = location.search.substr(1);
    var params = {};
    paramsString.split("&").forEach(function(part) {
      var item = part.split("=");
      params[item[0]] = decodeURIComponent(item[1]);
    });

    if (params.doc_lang) {
        const langSelect = document.getElementById('doc_lang');
        langSelect.value = params.doc_lang;
    }

    const FILTER_RE = /(ft|ff|fo|fv|fc)[0-9]+$/;
    let filterDefined = [];
    Object.keys(params).forEach(function (key) {
        if (!key.match(FILTER_RE)) {
            return;
        }

        const filterNo = key.substr(2);
        if (filterDefined.indexOf(filterNo) === -1) {
            filterDefined.push(filterNo);
        }
    });

    if (filterDefined.length === 0) {
        return;
    }

    filterDefined.forEach(function (addedNo) {
        add_new_adv_search();
        const new_adv_search = document.getElementById('adv_search' + adv_search_lines);

        Object.keys(params).forEach(function (key) {
            if (!key.match(FILTER_RE)) {
                return;
            }

            const filterNo = key.substr(2);
            if (filterNo !== addedNo) {
                return;
            }

            const inputName = key.substr(0, 2);
            const children = new_adv_search.children;
            for (let i = 0; i < children.length; i++) {
                const elem = children[i];
                const value = params[inputName + addedNo];
                if (elem.getAttribute('name') === inputName + adv_search_lines) {
                    if (inputName === 'fc') {
                        elem.checked = true;
                    } else {
                        elem.value = value;
                    }
                }
            }
        })
    });

    search_more();
}

function on_submit() {
    const adv_search = document.getElementById('adv_search');
    if (adv_search.style.display === 'none') {
        adv_search.remove();
    }

    const form = document.getElementById('search_form');
    form.submit();
    return false;
}
