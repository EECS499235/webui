import socket
import ssl
import OpenSSL.crypto # You may need to install this library
from urllib.parse import urlparse
import hydra
from omegaconf import DictConfig, OmegaConf

def get_website_certificate(host, port=443):
    """
    Retrieves the X.509 certificate from a specified host and port.
    """
    try:
        # Create a standard TCP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Wrap the socket with SSL, using default system certificates for context
        context = ssl.create_default_context()
        conn = context.wrap_socket(sock, server_hostname=host)
        
        # Connect to the host and port
        conn.connect((host, port))
        
        # Get the peer certificate (the server's certificate)
        cert = conn.getpeercert()
        
        # Close the connection
        conn.close()
        
        return cert
    except socket.error as e:
        print(f"Socket error: {e}")
        return None
    except ssl.SSLError as e:
        print(f"SSL error: {e}")
        return None


@hydra.main(version_base=None, config_path=".", config_name="fwd")
def checktls_main (cfg : DictConfig) -> None:
    print(OmegaConf.to_yaml(cfg))

    # Example usage:
    parsed_url = urlparse(cfg.LOGIN_URL)
    host_name = parsed_url.hostname

    certificate_info = get_website_certificate(host_name)

    if certificate_info:
        print(f"Certificate details for {host_name}:")
        # You can print specific fields from the certificate dictionary
        # Example: Subject common name (CN)
        subject = dict(x[0] for x in certificate_info['subject'])
        print(f"  Common Name (CN): {subject.get('commonName', 'N/A')}")
        print(f"  Organization (O): {subject.get('organizationName', 'N/A')}")
        print(f"  Issuer: {dict(x[0] for x in certificate_info['issuer']).get('commonName', 'N/A')}")
        print(f"  NotBefore: {certificate_info['notBefore']}")
        print(f"  NotAfter: {certificate_info['notAfter']}")

if __name__ == "__main__":
    checktls_main()