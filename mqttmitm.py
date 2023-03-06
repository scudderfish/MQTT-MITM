from grottproxy import Proxy
from mqttconf import Conf
import sys
verrel = "0.0.1"


# proces config file
conf = Conf(verrel)

# print configuration
if conf.verbose:
    conf.print()

# To test config only remove # below
# sys.exit(1)

proxy = Proxy(conf)
try:
    proxy.main(conf)
except KeyboardInterrupt:
    print("Ctrl C - Stopping server")
    try:
        proxy.on_close(conf)
    except:
        print("\t - no ports to close")
    sys.exit(1)
