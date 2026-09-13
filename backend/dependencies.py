from config import settings
from services.data_loader import load_network_data
from services.algorithms import CascadeSimulator

# Global instances to avoid rebuilding on every request
_simulator_instance = None
_network_data = None

def get_network_data():
    global _network_data
    if _network_data is None:
        _network_data = load_network_data(settings.NETWORK_JSON_PATH)
    return _network_data

def get_simulator():
    global _simulator_instance
    if _simulator_instance is None:
        net_data = get_network_data()
        _simulator_instance = CascadeSimulator(net_data)
    return _simulator_instance

def reset_simulator():
    """Useful for testing to force a reload."""
    global _simulator_instance, _network_data
    _simulator_instance = None
    _network_data = None
