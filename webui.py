# webui.py: automate the TLS certificate upload in Web UI
# Author: Victor Liu <vyl@umich.edu>
# auto load TLS priv key and certificate on Forwardnetwork app 
# source: https://chatgpt.com/g/g-p-68afd931be008191b8e12acaa7d5e007-dsp-topics/shared/c/691f9451-4884-8328-92b0-7302554749ae?owner_user_id=user-eMZUQ4EsYb6bXaIkYKdttTw3

import hydra
from omegaconf import DictConfig, OmegaConf

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import os

try:
    FWD_USER = os.environ["FWD_USER"]
    FWD_PASS = os.environ["FWD_PASS"]
except KeyError:
    # Handle the case where the key is missing
    print("Error: The FWD_USER or FWD_PASS environment variables are not set.")
    # You can also exit the program or raise a custom exception here if needed
    raise SystemExit(1)

#FILE1_PATH = r"/absolute/path/to/private_key.pem"
#FILE2_PATH = r"/absolute/path/to/certificate.pem"

# XPaths you MUST customize:
#XPATH_LOGIN_EMAIL   = "//input[@type='email' or @name='username' or @id='username']"
XPATH_LOGIN_EMAIL   = "//*[@id='field-1']"
#XPATH_LOGIN_PW      = "//input[@type='password' or @name='password' or @id='password']"
XPATH_LOGIN_PW      = "//*[@id='field-4']"
#XPATH_LOGIN_BUTTON  = "//button[contains(., 'Log in') or contains(., 'Login')]"
XPATH_LOGIN_BUTTON  = "//*[@id='button-11']"
# Button that opens your upload dialog (you must set this)
XPATH_OPEN_DIALOG_BUTTON = "//*[@id='main']/div/div/section/div[2]/section/div[2]/button"

#"//button[contains(., 'Upload') or contains(., 'New')]"

# Optional: specific locator for the dialog container
# Forward uses a portal root `#layers`, dialogs often use role="dialog"
XPATH_DIALOG = "//*[@id='layers']//*[@role='dialog']"
XPATH_UPLOAD_BUTTON = "//*[@id='layers']/div/div/div/div[2]/form/div[2]/div/span/button"

XPATH_DIALOG_LAYER3 = "//*[@id='layers']//*[@role='dialog']"
XPATH_UPLOAD_CONFIRM = "//*[@id='layers']/div[1]/div/div/button"

# ---------------------------------------------------
# Helper functions
# ---------------------------------------------------
def wait_for(driver, timeout=40):
    return WebDriverWait(driver, timeout)

def wait_and_find(driver, by, value, timeout=40):
    return wait_for(driver, timeout).until(EC.presence_of_element_located((by, value)))

def wait_and_click(driver, by, value, timeout=40):
    el = wait_for(driver, timeout).until(EC.element_to_be_clickable((by, value)))
    el.click()
    return el


@hydra.main(version_base=None, config_path=".", config_name="fwd_old")
def webui_main (cfg : DictConfig) -> None:
    print(OmegaConf.to_yaml(cfg))
    # ---------------------------------------------------
    # Main script
    # ---------------------------------------------------
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(), options=options)
    wait = WebDriverWait(driver, 15)

    try:
        # 1. Go to login page
        driver.get(cfg.LOGIN_URL)

        # 2. Fill in login form
        email_input = wait_and_find(driver, By.XPATH, XPATH_LOGIN_EMAIL, timeout=20)
        password_input = wait_and_find(driver, By.XPATH, XPATH_LOGIN_PW, timeout=20)

        email_input.clear()
        email_input.send_keys(FWD_USER)
        password_input.clear()
        password_input.send_keys(FWD_PASS)

        # 3. Click login
        wait_and_click(driver, By.XPATH, XPATH_LOGIN_BUTTON, timeout=20)

        # 4. Wait for the SPA shell to load (#nav/#main)
        #    This indicates that the main Forward app has loaded.
        wait_and_find(driver, By.ID, "nav", timeout=30)
        wait_and_find(driver, By.ID, "main", timeout=30)

        # (Optional) small pause to let JS finish initial render
        time.sleep(2)

        # 5. Navigate (if needed) to the page with the upload button.
        driver.get(cfg.TARGET_PAGE_URL)

        # 6. Click the button that opens the upload dialog
        wait_and_click(driver, By.XPATH, XPATH_OPEN_DIALOG_BUTTON, timeout=20)

        # 7. Wait for dialog to appear in #layers
        dialog = wait_and_find(driver, By.XPATH, XPATH_DIALOG, timeout=20)

        #wait = WebDriverWait(driver, 20)
        
        ## Old code, see new code below

        # 8. Find file inputs *inside* the dialog and upload two files
        # Option A: there are multiple <input type="file"> elements
        #file_inputs = dialog.find_elements(By.CSS_SELECTOR, "input[type='file']")
        #if len(file_inputs) < 2:
        #    raise RuntimeError(f"Expected at least 2 file inputs, found {len(file_inputs)}")

        #file_inputs[0].send_keys(FILE1_PATH)
        #file_inputs[1].send_keys(FILE2_PATH)

        # If instead there is ONE <input type="file" multiple>, do this instead:
        # file_inputs[0].send_keys(FILE1_PATH + "\n" + FILE2_PATH)
        # --- 1) Find the two <input type="file"> elements inside the dialog ---

        # Option A (recommended): use the name attributes
        private_key_input = dialog.find_element(By.NAME, "privateKey")
        certificate_input = dialog.find_element(By.NAME, "certificate")

        # (Option B: by id, if you prefer; but ids like fc-$25 can change)
        #private_key_input = dialog.find_element(By.ID, "fc-$25")
        #certificate_input = dialog.find_element(By.ID, "fc-$26")

        # --- 2) Send the file paths ---

        private_key_input.send_keys(cfg.FILE1_PATH)
        certificate_input.send_keys(cfg.FILE2_PATH)
        
        # 9. Click the dialog's submit/confirm button
        # Adjust XPath based on your dialog's button text
        #submit_button = dialog.find_element(
        #    By.XPATH,
        #    ".//button[contains(., 'Upload') or contains(., 'Save') or contains(., 'Submit')]"
        #)
        # --- 3) Wait for the Upload button to become enabled and clickable ---

        upload_button = wait.until(
            EC.element_to_be_clickable((
                By.XPATH,
                XPATH_UPLOAD_BUTTON
            ))
        )
        #submit_button.click()

        # --- 4) Click Upload ---
        upload_button.click()

        # Then confirm upload button popup
        
        # Do not have to find dialog in layer 3. The button can be found & clicked directly.
        # dialog = wait_and_find(driver, By.XPATH, XPATH_DIALOG_LAYER3, timeout=20)
        
        wait_and_click(driver, By.XPATH, XPATH_UPLOAD_CONFIRM, timeout=20)
        
        # 10. Wait for upload to finish or success message
        time.sleep(5)
        print("Files uploaded successfully.")

    finally:
        driver.quit()

if __name__ == "__main__":
    webui_main()