from kb.modules.m3_business_rules import lookup_rule
from kb.modules.m1_signal_dict import lookup_signal
from kb.modules.m4_routing_config import lookup_routing


def lookup_kpi(kpi_query: str):
    return lookup_rule(kpi_query)


def lookup_signal_field(signal_query: str):
    return lookup_signal(signal_query)


def lookup_vehicle_routing(car_model: str, software_version: str):
    return lookup_routing(car_model, software_version)
