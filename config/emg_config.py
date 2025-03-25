# config/emg_config.py
# EMG procedure configurations for validation
EMG_CONFIGURATIONS = {
    # Define valid EMG bundles
    "BUNDLES": {
        "EMG Visit": ["95910", "95886"],
        "EMG Visit - 2": ["95910", "95885"],
        "EMG Visit - 3": ["95913", "95886"],
        "EMG Visit - 4": ["95913", "95885"],
        "EMG Visit - 5": ["95910", "99203", "95885"],
        "EMG Visit - 6": ["95910", "99203", "95886"],
        "EMG Visit - 7": ["95909", "95885"]
    },
    
    # Define allowed units for EMG codes
    "ALLOWED_UNITS": {
        # Study codes - always 1 unit
        "95907": 1,  # NCS 1-2
        "95908": 1,  # NCS 3-4
        "95909": 1,  # NCS 5-6
        "95910": 1,  # NCS 7-8
        "95911": 1,  # NCS 9-10
        "95912": 1,  # NCS 11-12
        "95913": 1,  # NCS 13+
        
        # Needle EMG codes - can have multiple units
        "95885": 4,  # Needle EMG limited (up to 4 units)
        "95886": 4,  # Needle EMG complete (up to 4 units)
        "95887": 1,  # Needle EMG non-limb muscles
        
        # Evaluation codes
        "99203": 1   # Office/outpatient visit new
    }
}