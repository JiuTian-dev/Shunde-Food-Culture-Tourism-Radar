# -*- coding: utf-8 -*-
"""线上验证：加载 Cloudflare Pages 站点，检查渲染与接口是否正常。"""
import sys
from playwright.sync_api import sync_playwright

URL = "https://shunde-food-radar.pages.dev"


def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"[pageerror] {e}"))

        page.goto(URL, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(2500)

        # 截图
        page.screenshot(path="C:/Temp/cfchat/shot_full.png", full_page=True)

        # 检查地图/榜单是否渲染出店铺
        body = page.inner_text("body")
        checks = {
            "包含店铺名": ("民信老铺" in body or "美姐粥档" in body or "欢姐" in body),
            "包含页面标题": ("顺德" in body),
        }

        # 点第一个店铺标记，看抽屉是否弹出
        marker = page.locator(".shop-dot, .dot, [class*=shop]").first
        drawer_ok = False
        try:
            if marker.count() > 0:
                marker.click(timeout=5000)
                page.wait_for_timeout(2000)
                page.screenshot(path="C:/Temp/cfchat/shot_drawer.png")
                drawer_ok = True
        except Exception as e:
            errors.append(f"[drawer] {e}")

        print("CHECKS:")
        for k, v in checks.items():
            print(f"  {k}: {'PASS' if v else 'FAIL'}")
        print(f"  店铺抽屉打开: {'PASS' if drawer_ok else 'FAIL(无标记可点)'}")
        print(f"CONSOLE ERRORS: {len(errors)}")
        for e in errors[:10]:
            print("  " + e)
        browser.close()


if __name__ == "__main__":
    sys.exit(main())
