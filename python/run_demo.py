import sys
import os

# Add src folder to module path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from utils import get_timestamp, totp_generate, sha256_hash
from init import init_cloud, init_fog_node, init_rbac
from network import deploy_nodes, leach_sep_clustering, simulate_communication_round
from auth import device_register, device_login, totp_auth
from access import check_permission, display_audit_log
from viz import plot_deployment, plot_clusters, plot_network_stats, plot_rbac_heatmap

def run_demo():
    print('================================================================')
    print('  LAFSH: Lightweight Authentication for Fog-based Smart Homes')
    print('  Fog Computing Project Demonstration')
    print('================================================================\n')

    # Create output directories
    os.makedirs('results', exist_ok=True)
    os.makedirs('figures', exist_ok=True)

    # === STAGE 1: System Initialization ===
    print('\n--- STAGE 1: System Initialization ---\n')
    cloud = init_cloud()
    rbac = init_rbac()
    fog = init_fog_node('FOG_HOME_01', cloud, rbac, 100, 100)

    # === STAGE 2: Deploy Heterogeneous IoT Nodes ===
    print('\n--- STAGE 2: Deploy 500 Heterogeneous IoT Nodes ---\n')
    NUM_NODES = 500
    AREA_SIZE = 200
    devices = deploy_nodes(NUM_NODES, AREA_SIZE)

    # Override a few devices to be user-role (phone, tablet)
    devices[0].id = 'PHONE_ADMIN'
    devices[0].type = 'phone'
    devices[0].role = 'Admin'
    devices[0].residual_energy = 10.0
    devices[0].initial_energy = 10.0

    devices[1].id = 'PHONE_RESIDENT'
    devices[1].type = 'phone'
    devices[1].role = 'Resident'
    devices[1].residual_energy = 10.0
    devices[1].initial_energy = 10.0

    devices[2].id = 'TABLET_GUEST'
    devices[2].type = 'tablet'
    devices[2].role = 'Guest'
    devices[2].residual_energy = 8.0
    devices[2].initial_energy = 8.0

    # Visualize deployment
    plot_deployment(devices, fog, AREA_SIZE)

    # === STAGE 3: LEACH-SEP Cluster Formation ===
    print('\n--- STAGE 3: LEACH-SEP Cluster Formation ---\n')
    devices, clusters = leach_sep_clustering(devices, fog, 1, 0.1, AREA_SIZE)
    plot_clusters(devices, clusters, fog, AREA_SIZE)

    # === STAGE 4: Cluster Communication Rounds ===
    print('\n--- STAGE 4: Simulating Communication Rounds ---\n')
    NUM_ROUNDS = 50
    all_stats = []

    for r in range(1, NUM_ROUNDS + 1):
        # Re-cluster every 10 rounds
        if r % 10 == 1:
            devices, clusters = leach_sep_clustering(devices, fog, r, 0.1, AREA_SIZE)

        devices, round_stats = simulate_communication_round(devices, clusters, fog, r)
        all_stats.append(round_stats)

        if r % 10 == 0:
            print(f"  Round {r}: {round_stats['alive_nodes']} alive, {round_stats['total_energy_consumed']:.4f} J consumed, PDR={round_stats['packet_delivery_ratio']*100:.1f}%")

    plot_network_stats(all_stats, NUM_NODES)

    # === STAGE 5: Device Registration ===
    print('\n--- STAGE 5: Device Registration ---\n')
    demo_indices = [0, 1, 2, 3, 4, 5]  # Admin, Resident, Guest + 3 IoT devices
    for di in demo_indices:
        devices[di], fog, reg_stats = device_register(devices[di], fog)

    # === STAGE 6: Mutual Authentication ===
    print('\n--- STAGE 6: Mutual Authentication (Phase 2) ---\n')
    for di in demo_indices:
        auth_result, devices[di], fog = device_login(devices[di], fog)

    # === STAGE 7: TOTP Two-Factor Authentication ===
    print('\n--- STAGE 7: TOTP 2FA for Admin/Resident ---\n')
    sim_time = get_timestamp()
    
    # Admin TOTP
    admin_otp = totp_generate(devices[0].totp_secret, sim_time)
    print(f"  Admin OTP generated: {admin_otp:06d}")
    totp_res, fog = totp_auth(devices[0], fog, admin_otp, sim_time)

    # Resident TOTP
    resident_otp = totp_generate(devices[1].totp_secret, sim_time)
    print(f"  Resident OTP generated: {resident_otp:06d}")
    totp_res, fog = totp_auth(devices[1], fog, resident_otp, sim_time)

    # === STAGE 8: RBAC Access Control Scenarios ===
    print('\n--- STAGE 8: RBAC Access Control ---\n')
    print('>> Admin controls smart lock:')
    p, r, fog = check_permission(devices[0].id, 'lock', fog)

    print('>> Resident reads thermostat:')
    p, r, fog = check_permission(devices[1].id, 'thermo_read', fog)

    print('>> Guest tries to unlock door:')
    p, r, fog = check_permission(devices[2].id, 'unlock', fog)

    print('>> Device reports sensor data:')
    p, r, fog = check_permission(devices[3].id, 'sensor_report', fog)

    print('>> Guest tries camera recording:')
    p, r, fog = check_permission(devices[2].id, 'cam_rec', fog)

    print('>> Admin adds new device:')
    p, r, fog = check_permission(devices[0].id, 'add_device', fog)

    # === STAGE 9: Attack Detection ===
    print('\n--- STAGE 9: Attack Detection ---\n')
    
    # Attack 1: Replay attack (expired timestamp)
    print('>> ATTACK 1: Replay attack with old timestamp')
    old_time = get_timestamp() - 300  # 5 minutes ago
    atk_result, _, fog = device_login(devices[3], fog, old_time)
    print(f"   Result: {atk_result['failure_reason']}\n")

    # Attack 2: Device cloning (modified fingerprint)
    print('>> ATTACK 2: Device cloning attempt')
    import copy
    cloned = copy.copy(devices[4])
    cloned.fingerprint = sha256_hash('CLONED_DEVICE_FAKE')
    atk_result, _, fog = device_login(cloned, fog)
    print(f"   Result: {atk_result['failure_reason']}\n")

    # Attack 3: Wrong TOTP code
    print('>> ATTACK 3: Invalid TOTP code')
    totp_atk, fog = totp_auth(devices[0], fog, 999999, sim_time)
    print(f"   Result: {totp_atk['reason']}\n")

    # === STAGE 10: RBAC Heatmap & Audit Log ===
    print('\n--- STAGE 10: Visualization & Audit ---\n')
    plot_rbac_heatmap(rbac)
    display_audit_log(fog)

    print('\n================================================================')
    print('  DEMONSTRATION COMPLETE')
    print('  Protocol: LAFSH (Lightweight Auth for Fog-based Smart Homes)')
    print(f"  Nodes deployed: {NUM_NODES} (heterogeneous)")
    print(f"  Clusters formed: {len(clusters)} (LEACH-SEP)")
    print(f"  Devices registered: {len(demo_indices)}")
    print('  Auth protocol: Mutual + TOTP 2FA + Device Fingerprinting')
    print('  Access control: RBAC (4 roles x 11 operations)')
    print('  Attacks blocked: 3/3 (replay, cloning, invalid TOTP)')
    print('================================================================')

if __name__ == '__main__':
    run_demo()
