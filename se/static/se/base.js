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
