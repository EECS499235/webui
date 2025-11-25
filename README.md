# Webui

Python script to automate TLS certificate refresh on Forward Network App. 

## Procedure

1. When the current TLS certificate is about to expire, an email should be received to notify TLS certificate owners to renew. 
2. UM InCommon webpage should be able to allow the owner to renew the certificate, by reusing the existing CSR or generate a new CSR. 
3. once this request to generated, wait for up to two business days until the certificate is generated. 
4. Run code ```python3 wasup.py``` to retrieve the TLS certificate and verify that matches the private key and CSR.  If both are correct, continue to next step.  This requires environment variables ```UM_USER```, ```UM_PASS``` to be exported in bash. 
5. Run code ```python3 webui.py``` to upload the private key and the certificate to Forward App.  This requires environment variables ```FWD_USER```, ```FWD_PASS``` to be exported in bash. 
6. Run code ```python3 checlTLS.py``` to verify the new certificate has been installed correctly. 

## Code
 
- webui.py: script to update Fwd App TLS certificate
- fwd.yaml: configuration YAML file.  change this file to make it work.
- fwd_old.yaml: configuration YAML file with old key/cert for testing
- checkTLS.py: run this to get TLS certificate of the website
- wasup.py: Script to obtain InCommon Certificate from UM ITS
- wasup.yaml: config for wasup.py
- certs/*: folder that stores private key, csr, and certificate files. Note: private key will not be uploaded in the repo. 


##  SETUP ENVIRONMENT VARIABLES

```
export FWD_USER = "admin" 
export FWD_PASS = "forward" # change!
```