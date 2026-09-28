// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

(() => {
    const darkThemes = ['ayu', 'navy', 'coal'];
    const lightThemes = ['light', 'rust'];

    const classList = document.getElementsByTagName('html')[0].classList;

    let lastThemeWasLight = true;
    for (const cssClass of classList) {
        if (darkThemes.includes(cssClass)) {
            lastThemeWasLight = false;
            break;
        }
    }

    const theme = lastThemeWasLight ? 'default' : 'dark';
    mermaid.initialize({ startOnLoad: true, theme });

    // Simplest way to make mermaid re-render the diagrams in the new theme is via refreshing the page
    // 注意：mdBook 0.5 起主题按钮 id 带 mdbook-theme- 前缀，且部分主题项可能被 assets/theme-names.js 移除

    for (const name of [...darkThemes, ...lightThemes]) {
        const button = document.getElementById('mdbook-theme-' + name);
        if (!button) continue;

        const isDark = darkThemes.includes(name);
        button.addEventListener('click', () => {
            if (lastThemeWasLight === isDark) {
                window.location.reload();
            }
        });
    }
})();
