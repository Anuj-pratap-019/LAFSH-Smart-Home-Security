from utils import generate_nonce, sha256_hash

class Cloud:
    def __init__(self, master_secret=None):
        self.id = 'CLOUD_01'
        self.master_secret = master_secret if master_secret is not None else generate_nonce(256)
        self.fog_registry = {}
        self.audit_log = []
        self.global_policy = {
            'max_session_duration': 3600,  # 1 hour
            'max_failed_attempts': 5,
            'totp_enabled': True
        }
        print(f"[CLOUD] Cloud server initialized (ID: {self.id})")

class FogNode:
    def __init__(self, fog_id, cloud, rbac, x=100, y=100):
        self.id = fog_id
        # Derive delegated secret from cloud master secret
        self.secret = sha256_hash(f"{cloud.master_secret}||{fog_id}")
        self.x = x
        self.y = y
        self.device_registry = {}  # DID -> dict
        self.active_sessions = {}  # DID -> dict
        self.rbac = rbac
        self.audit_log = []
        self.clock_delta = 120          # Max timestamp skew (seconds)
        self.session_timeout = 3600     # Session expiry (seconds)
        self.failed_attempts = {}       # DID -> int
        self.residual_energy = float('inf')
        self.comm_range = float('inf')
        print(f"[FOG] Fog node initialized (ID: {self.id}) at position ({self.x:.0f}, {self.y:.0f})")

class RBAC:
    def __init__(self):
        self.roles = ['Admin', 'Resident', 'Guest', 'Device']
        self.operations = ['lock', 'unlock', 'cam_live', 'cam_rec',
                           'thermo_set', 'thermo_read', 'lights',
                           'add_device', 'view_logs', 'firmware', 'sensor_report']
        
        # Permission matrix: rows=roles, cols=operations (1=allow, 0=deny)
        self.permission_matrix = [
            [1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1],  # Admin
            [1,   1,   1,   0,   1,   1,   1,   0,   1,   0,   1],  # Resident
            [0,   0,   1,   0,   0,   1,   1,   0,   0,   0,   1],  # Guest
            [0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   1]   # Device
        ]
        
        # Role -> row index map
        self.role_index = {role: i for i, role in enumerate(self.roles)}
        
        # Operation -> col index map
        self.op_index = {op: i for i, op in enumerate(self.operations)}
        
        # Guest time restrictions (hours in 24h format)
        self.guest_window = {
            'start_hour': 9,   # 09:00
            'end_hour': 22     # 22:00
        }
        print(f"[RBAC] Access control initialized: {len(self.roles)} roles x {len(self.operations)} operations")

def init_cloud(master_secret=None):
    return Cloud(master_secret)

def init_fog_node(fog_id, cloud, rbac, x=100, y=100):
    return FogNode(fog_id, cloud, rbac, x, y)

def init_rbac():
    return RBAC()
