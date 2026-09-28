// 主题选择器中文化：仅保留"白天模式"（light）与"黑夜模式"（coal），其余主题项移除
(function () {
    "use strict";

    var themeNames = {
        "mdbook-theme-light": "白天模式",
        "mdbook-theme-coal": "黑夜模式"
    };

    var toggle = document.getElementById("mdbook-theme-toggle");
    if (toggle) {
        toggle.title = "切换主题";
        toggle.setAttribute("aria-label", "切换主题");
    }

    var list = document.getElementById("mdbook-theme-list");
    if (!list) return;

    Array.prototype.forEach.call(list.querySelectorAll("li"), function (item) {
        var button = item.querySelector("button.theme");
        var name = button && themeNames[button.id];
        if (name) {
            button.textContent = name;
        } else {
            item.parentNode.removeChild(item);
        }
    });
})();
