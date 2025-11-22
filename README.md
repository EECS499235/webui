# Webui

Python script to automate TLS certificate refresh on Forward Network App. 

- webui.py: script to update Fwd App TLS certificate
- fwd.yaml: configuration YAML file.  change this file to make it work.
- fwd_old.yaml: configuration YAML file with old key/cert for testing
- checkTLS.py: run this to get TLS certificate of the website


##  SETUP ENVIRONMENT VARIABLES

```
export FWD_USER = "admin" 
export FWD_PASS = "forward" # change!
```