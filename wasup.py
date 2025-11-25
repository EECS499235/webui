# wasup.py
# This script will download InCommon Certificate from Wasup page by a permitted UM user

# Author: Victor Liu <vyl@umich.edu>
# Following code is modified from webui.py in this repo. 
# 
import hydra
from omegaconf import DictConfig, OmegaConf

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import os
import re
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization

try:
    # We might want to complete the UM's MFA authentication using user/pass/methods below. 
    UM_USER = os.environ["UM_USER"]
    UM_PASS = os.environ["UM_PASS"]
    #UM_MFA  = os.environ["UM_MFA"] 
    # which MFA method used for this authentication. 
    # This could be changing over time and break the automation if we do not exhaust all possibilities)
except KeyError:
    # Handle the case where the key is missing
    print("Error: The UM_USER or UM_PASS environment variables are not set.")
    # You can also exit the program or raise a custom exception here if needed
    raise SystemExit(1)

# XPaths you MUST customize:
#XPATH_LOGIN_EMAIL   = "//input[@type='email' or @name='username' or @id='username']"
XPATH_LOGIN_EMAIL   = "//*[@id='username']"
#XPATH_LOGIN_PW      = "//input[@type='password' or @name='password' or @id='password']"
XPATH_LOGIN_PW      = "//*[@id='password']"
#XPATH_LOGIN_BUTTON  = "//button[contains(., 'Log in') or contains(., 'Login')]"
XPATH_LOGIN_BUTTON  = "//*[@id='loginSubmit']"

# Button that opens your upload dialog (you must set this)
XPATH_MY_DEVICE_BUTTON = "//*[@id='trust-browser-button']"

#"//button[contains(., 'Upload') or contains(., 'New')]"

# Optional: specific locator for the dialog container
# Forward uses a portal root `#layers`, dialogs often use role="dialog"
XPATH_DIALOG = "//*[@id='layers']//*[@role='dialog']"
XPATH_UPLOAD_BUTTON = "//*[@id='layers']/div/div/div/div[2]/form/div[2]/div/span/button"

XPATH_DIALOG_LAYER3 = "//*[@id='layers']//*[@role='dialog']"
XPATH_UPLOAD_CONFIRM = "//*[@id='layers']/div[1]/div/div/div[2]/form/div[2]/button[1]"

# "//*[@id='layers']/div[1]/div/div/button"

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

def extract_cert_chain_pem(driver):
    """
    Use Selenium to locate and extract the TLS certificate chain
    from the HTML page. Assumes the HTML structure like:

    <th>SSL Certificate:</th><td><pre>-----BEGIN CERTIFICATE----- ...</pre></td>
    """
    # XPath: find the <pre> that is in the same row as the "SSL Certificate:" header
    pre_element = driver.find_element(
        By.XPATH,
        "//tr[th[normalize-space()='SSL Certificate:']]/td/pre"
    )
    cert_chain_pem = pre_element.text.strip()
    return cert_chain_pem

def extract_csr_pem(driver):
    """
    Use Selenium to locate and extract the CSR from the HTML page:

    <tr>
      <th>CSR:</th>
      <td class="textarea_scroll">
        <pre>-----BEGIN CERTIFICATE REQUEST----- ...</pre>
      </td>
    </tr>
    """
    pre_element = driver.find_element(
        By.XPATH,
        "//tr[th[normalize-space()='CSR:']]/td/pre"
    )
    csr_pem = pre_element.text.strip()
    return csr_pem


def get_leaf_cert_pem(cert_chain_pem):
    """
    Given a PEM chain containing one or more certificates,
    return the FIRST certificate block (the leaf).
    """
    pattern = r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----"
    matches = re.findall(pattern, cert_chain_pem, flags=re.DOTALL)
    if not matches:
        raise ValueError("No PEM certificates found in extracted text.")
    return matches[0]


def load_public_key_from_cert(cert_pem: str):
    cert = x509.load_pem_x509_certificate(cert_pem.encode("ascii"))
    return cert.public_key()


def load_public_key_from_private_key_file(key_path: Path, password: str | None = None):
    key_bytes = Path(key_path).read_bytes()
    if password is not None:
        password_bytes = password.encode("utf-8")
    else:
        password_bytes = None

    private_key = serialization.load_pem_private_key(
        key_bytes,
        password=password_bytes,
    )
    return private_key.public_key()

def load_csr_from_pem_string(csr_pem: str):
    return x509.load_pem_x509_csr(csr_pem.encode("ascii"))


def load_csr_from_file(csr_path: Path):
    csr_pem = Path(csr_path).read_text(encoding="utf-8")
    return x509.load_pem_x509_csr(csr_pem.encode("ascii"))


def public_keys_match(pub_from_cert, pub_from_key) -> bool:
    """
    Compare two public keys (RSA, EC, etc.) by their public numbers.
    Works for typical TLS keys.
    """
    # For RSA / EC, `public_numbers()` exists and returns a comparable object
    try:
        return pub_from_cert.public_numbers() == pub_from_key.public_numbers()
    except Exception as e:
        print(f"Could not compare public keys: {e}", file=sys.stderr)
        return False

@hydra.main(version_base=None, config_path=".", config_name="wasup")
def wasup_main (cfg : DictConfig) -> None:
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

        # 2. SSO login below unless we do not need it.
        email_input = wait_and_find(driver, By.XPATH, XPATH_LOGIN_EMAIL, timeout=20)
        password_input = wait_and_find(driver, By.XPATH, XPATH_LOGIN_PW, timeout=20)

        email_input.clear()
        email_input.send_keys(UM_USER)
        password_input.clear()
        password_input.send_keys(UM_PASS)

        # 3. Click login
        wait_and_click(driver, By.XPATH, XPATH_LOGIN_BUTTON, timeout=20)

        # 3.5 Click "Yes this is my device"
        wait_and_click(driver, By.XPATH, XPATH_MY_DEVICE_BUTTON, timeout=20)


        # 4. Wait for the SPA shell to load (#nav/#main)
        #    This indicates that the main Forward app has loaded.
        wait_and_find(driver, By.ID, "service_configuration", timeout=30)
        #wait_and_find(driver, By.ID, "footer", timeout=30)

        # (Optional) small pause to let JS finish initial render
        #time.sleep(2)

        # parsing the private key file

        key_path = cfg.KEY_PATH
        csr_file_path = cfg.CSR_PATH
        key_password =None

        if not os.path.isfile(key_path):
            print(f"Private key file not found: {key_path}", file=sys.stderr)
            sys.exit(1)

        if not os.path.isfile(csr_file_path):
            print(f"CSR file not found: {csr_file_path}", file=sys.stderr)
            sys.exit(1)

    
        # 5. Navigate (if needed) to the page with the upload button.
        driver.get(cfg.TARGET_PAGE_URL)

        # 1. Extract the certificate chain from the page
        cert_chain_pem = extract_cert_chain_pem(driver)
        print("=== Extracted certificate chain from page ===")
        print(cert_chain_pem)
        print("============================================\n")

        # 2. Get just the leaf certificate (first PEM block)
        leaf_cert_pem = get_leaf_cert_pem(cert_chain_pem)

        # 3. Load public keys from cert and private key
        pub_from_cert = load_public_key_from_cert(leaf_cert_pem)
        pub_from_key = load_public_key_from_private_key_file(key_path, key_password)

        # 4. Compare
        if public_keys_match(pub_from_cert, pub_from_key):
            print("✅ The certificate's public key MATCHES the given private key.")
        else:
            print("❌ The certificate's public key does NOT match the given private key.")

        # 5. Extract CSR from page
        page_csr_pem = extract_csr_pem(driver)
        print("\n=== Extracted CSR from page ===")
        print(page_csr_pem)
        print("================================\n")

        # 6. Load CSRs: one from page, one from file
        csr_from_page = load_csr_from_pem_string(page_csr_pem)
        csr_from_file = load_csr_from_file(csr_file_path)

        # 7. Compare CSR subjects
        same_subject = csr_from_page.subject == csr_from_file.subject

        # 8. Compare CSR public keys
        csr_pub_from_page = csr_from_page.public_key()
        csr_pub_from_file = csr_from_file.public_key()
        same_pubkey = public_keys_match(csr_pub_from_page, csr_pub_from_file)

        # 9. Optional: compare raw DER encodings
        same_der = (
            csr_from_page.public_bytes(serialization.Encoding.DER)
            == csr_from_file.public_bytes(serialization.Encoding.DER)
        )

        # 10. Print results
        if same_subject and same_pubkey:
            print("✅ CSR from page matches CSR from file (subject and public key are identical).")
        else:
            print("❌ CSR from page does NOT fully match CSR from file.")
            print(f"   - Same subject?:  {same_subject}")
            print(f"   - Same pubkey?:   {same_pubkey}")

        print(f"   - Same DER bytes?: {same_der}")

        # 11. Wait for upload to finish or success message
        time.sleep(5)
        print("Files uploaded successfully.")

    finally:
        driver.quit()

if __name__ == "__main__":
    wasup_main()