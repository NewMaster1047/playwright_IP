from playwright.sync_api import sync_playwright


playwright = sync_playwright().start()
browser_path = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
browser = playwright.chromium.launch(executable_path=browser_path, headless=False)


context = browser.new_context()
page = context.new_page()


# Start waiting for the download
with page.expect_download() as download_info:
    # Perform the action that initiates download
    page.get_by_text("Download file").click()
download = download_info.value

# Wait for the download process to complete and save the downloaded file somewhere
download.save_as("/path/to/save/at/" + download.suggested_filename)




