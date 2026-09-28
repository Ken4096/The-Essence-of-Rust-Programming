// 顶部广告横幅：由 book.toml 的 additional-js 注入。
// 该脚本以同步 <script> 出现在每个页面 body 末尾，执行时挂载点必定已在 DOM 中。
(function () {
    "use strict";

    var BANNER_ID = "mdbook-ad-banner";
    // 广告图片：内联的 WebP data URI。
    // mdBook 只复制 src/ 下的非 .md 文件，以及 additional-css/js 里列出的文件；
    // 每次构建还会清空整个 book/，所以放在 assets/ 里的图片没法自动进入产物，
    // 直接打开 file:// 或本地预览时必然 404。内联后广告图随脚本一起打包，无构建步骤。
    // 图片源文件仍保存在 assets/ 下，换了图必须重新生成对应的那条串（需 ffmpeg 与 base64）：
    //   ffmpeg -v error -i assets/ad-aliyun.png   -c:v libwebp -quality 82 -f webp - | base64 -w0
    //   ffmpeg -v error -i assets/ad-yecaoyun.png -c:v libwebp -quality 82 -f webp - | base64 -w0
    // 输出前面拼上 "data:image/webp;base64," 即可。漏了这步页面会一直显示旧图。
    var IMG_ALIYUN = "data:image/webp;base64,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";
    var IMG_YECAOYUN = "data:image/webp;base64,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";

    // 广告数据：img 直接用内联的 WebP data URI，不依赖任何外部文件。
    // tip 是鼠标悬停提示的文字（提示框由本文件运行时创建，样式在 ads.css），
    // alt 是图片加载失败时显示的文字，同时充当链接的无障碍名称。
    var ADS = [
        {
            img: IMG_ALIYUN,
            href: "https://www.aliyun.com/minisite/goods?userCode=udrxno9h",
            alt: "阿里云优惠活动",
            tip: "感谢支持，学习愉快！"
        },
        {
            img: IMG_YECAOYUN,
            href: "https://www.yecaoyun.com/Page/offers.html?aff=7257",
            alt: "野草云优惠活动",
            tip: "感谢支持，学习愉快！"
        }
    ];

    // 不投放广告的页面，按章节名精确匹配（章节名即 <title> 中 " - " 之前的部分）。
    // 注意：mdBook 把首章同时输出为 index.html 和 introduction.html，
    // 两页 <title> 都是 "前言 - ..."，所以这一条同时覆盖首页和前言页。
    var AD_EXCLUDED_PAGES = ["前言"];

    // 读：当前页面的章节名，即 <title> 中 " - " 之前的部分
    function pageTitle() {
        var title = document.title || "";
        var i = title.indexOf(" - ");
        return i === -1 ? title : title.slice(0, i);
    }

    // 状态查询：当前页面是否投放广告
    function shouldShowAds() {
        return AD_EXCLUDED_PAGES.indexOf(pageTitle()) === -1;
    }

    // 读：站点根路径前缀。
    // mdBook 在 <head> 里以顶层 const 声明 path_to_root（不是 window 属性），
    // 用 typeof 兜底，避免它将来被移除时抛 ReferenceError。
    function siteRoot() {
        return typeof path_to_root === "string" ? path_to_root : "";
    }

    // 创建：单条广告 = 一张图片套一个链接
    function createAd(ad, root) {
        var link = document.createElement("a");
        link.href = ad.href;
        link.target = "_blank";
        link.rel = "noopener sponsored";
        // 用 data-tip 而非 title：title 的原生提示框有约 1 秒延迟
        link.setAttribute("data-tip", ad.tip || "");

        var img = document.createElement("img");
        img.src = root + ad.img;
        img.alt = ad.alt || "";
        img.decoding = "async";

        link.appendChild(img);
        return link;
    }

    // 创建：整条横幅
    function createBanner() {
        var root = siteRoot();
        var banner = document.createElement("div");
        banner.id = BANNER_ID;
        banner.setAttribute("role", "complementary");
        banner.setAttribute("aria-label", "赞助商链接");

        ADS.forEach(function (ad) {
            banner.appendChild(createAd(ad, root));
        });

        return banner;
    }

    // ===== 悬停提示：跟随鼠标位置显示 =====
    // 原生 title 的提示框约 1 秒后才出现，且延迟无法调节，故自己实现一个。
    var TIP_ID = "mdbook-ad-tip";
    var TIP_OFFSET = 14;    // 提示框与鼠标光标的间距
    var tipEl = null;

    // 创建：提示元素，整个页面共用一个，首次用到时才建
    function ensureTip() {
        if (!tipEl) {
            tipEl = document.createElement("div");
            tipEl.id = TIP_ID;
            tipEl.setAttribute("role", "tooltip");
            document.body.appendChild(tipEl);
        }
        return tipEl;
    }

    // 写：把提示框摆到光标右下方；贴边放不下时翻到另一侧，避免被视口裁掉
    function moveTip(x, y) {
        if (!tipEl) return;
        var w = tipEl.offsetWidth;
        var h = tipEl.offsetHeight;
        var left = x + TIP_OFFSET;
        var top = y + TIP_OFFSET + 6;

        if (left + w > window.innerWidth) left = x - w - TIP_OFFSET;
        if (top + h > window.innerHeight) top = y - h - TIP_OFFSET;

        tipEl.style.left = left + "px";
        tipEl.style.top = top + "px";
    }

    // 写：显示提示（先填内容再定位，否则首帧量到的宽高是上一次的）
    function showTip(text, x, y) {
        var el = ensureTip();
        el.textContent = text;
        el.style.display = "block";
        moveTip(x, y);
    }

    // 写：隐藏提示
    function hideTip() {
        if (tipEl) tipEl.style.display = "none";
    }

    // 组装：把提示行为挂到横幅上（事件委托，无需逐个链接绑定）
    function bindTip(banner) {
        banner.addEventListener("mouseover", function (e) {
            var link = e.target.closest("a[data-tip]");
            if (link) showTip(link.getAttribute("data-tip"), e.clientX, e.clientY);
        });

        banner.addEventListener("mousemove", function (e) {
            if (e.target.closest("a[data-tip]")) moveTip(e.clientX, e.clientY);
        });

        banner.addEventListener("mouseleave", hideTip);
    }

    // 组装：把横幅挂到 sticky 菜单栏之上。
    // 该占位元素是 mdBook 0.5.x 为菜单栏预留的 sticky 槽位，
    // 横幅插在它之前，位置补偿由 assets/ads.css 负责。
    function mount() {
        if (document.getElementById(BANNER_ID)) return;
        if (!shouldShowAds()) return;                // 前言等页面不投放广告

        var anchor = document.getElementById("mdbook-menu-bar-hover-placeholder");
        if (!anchor || !anchor.parentNode) return;   // 页面结构变化时快速失败

        var banner = createBanner();
        anchor.parentNode.insertBefore(banner, anchor);
        bindTip(banner);
    }

    mount();

    // 兜底：万一将来 mdBook 把 additional-js 挪到 <head>，等 DOM 就绪再挂一次
    if (!document.getElementById(BANNER_ID) && document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", mount);
    }
})();
