import sys
import os
import copy

# Add src folder to module path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from utils import get_timestamp, totp_generate, sha256_hash
from init import init_cloud, init_fog_node, init_rbac
from network import deploy_nodes
from auth import device_register, device_login, totp_auth
from access import check_permission

def run_security_analysis():
    print('================================================================')
    print('  LAFSH Security Analysis - Attack Scenario Testing')
    print('================================================================\n')

    # Setup
    cloud = init_cloud()
    rbac = init_rbac()
    fog = init_fog_node('FOG_SEC', cloud, rbac)
    devices = deploy_nodes(10, 100)

    # Make device 1 Admin
    devices[0].id = 'SEC_ADMIN'
    devices[0].role = 'Admin'

    # Register and authenticate device 1
    devices[0], fog, _ = device_register(devices[0], fog)
    auth_res, devices[0], fog = device_login(devices[0], fog)
    sim_time = get_timestamp()
    otp = totp_generate(devices[0].totp_secret, sim_time)
    totp_res, fog = totp_auth(devices[0], fog, otp, sim_time)

    # Register device 2 as normal device
    devices[1].id = 'SEC_LOCK'
    devices[1].role = 'Device'
    devices[1].capability_mask = 0b10101  # lock capabilities
    devices[1], fog, _ = device_register(devices[1], fog)
    auth_res_d2, devices[1], fog = device_login(devices[1], fog)

    passed = 0
    total = 6

    print('\n========== ATTACK SCENARIOS ==========\n')

    # Attack 1: Replay Attack
    print('--- TEST 1: Replay Attack ---')
    print('Scenario: Attacker captures M1 and replays it 5 minutes later')
    old_time = get_timestamp() - 300
    result, _, fog = device_login(devices[1], fog, old_time)
    if not result['success'] and 'Timestamp' in result['failure_reason']:
        print(f"RESULT: ATTACK BLOCKED - {result['failure_reason']}")
        passed += 1
    else:
        print('RESULT: VULNERABILITY - Attack not detected!')

    # Attack 2: Device Cloning
    print('\n--- TEST 2: Device Cloning ---')
    print('Scenario: Attacker creates clone with different hardware fingerprint')
    clone = copy.copy(devices[1])
    clone.fingerprint = sha256_hash('FAKE_CLONED_HARDWARE')
    result, _, fog = device_login(clone, fog)
    if not result['success'] and 'CLONING' in result['failure_reason']:
        print(f"RESULT: ATTACK BLOCKED - {result['failure_reason']}")
        passed += 1
    else:
        print('RESULT: VULNERABILITY - Attack not detected!')

    # Attack 3: Impersonation
    print('\n--- TEST 3: Impersonation ---')
    print('Scenario: Attacker tries to login with wrong credentials')
    impersonator = copy.copy(devices[1])
    impersonator.credentials = copy.copy(devices[1].credentials)
    impersonator.credentials['A_device'] = sha256_hash('WRONG_SECRET')
    result, _, fog = device_login(impersonator, fog)
    if not result['success'] and 'invalid' in result['failure_reason'].lower():
        print(f"RESULT: ATTACK BLOCKED - {result['failure_reason']}")
        passed += 1
    else:
        print('RESULT: VULNERABILITY - Attack not detected!')

    # Attack 4: Invalid TOTP
    print('\n--- TEST 4: TOTP Brute Force ---')
    print('Scenario: Attacker guesses random 6-digit TOTP codes')
    result, fog = totp_auth(devices[0], fog, 123456, sim_time)
    if not result['success']:
        print(f"RESULT: ATTACK BLOCKED - {result['reason']}")
        passed += 1
    else:
        print('RESULT: VULNERABILITY - Attack not detected!')

    # Attack 5: Privilege Escalation
    print('\n--- TEST 5: Privilege Escalation ---')
    print('Scenario: Device-role node tries Admin operation (firmware update)')
    permitted, reason, fog = check_permission(devices[1].id, 'firmware', fog)
    if not permitted:
        print(f"RESULT: ATTACK BLOCKED - {reason}")
        passed += 1
    else:
        print('RESULT: VULNERABILITY - Privilege escalation possible!')

    # Attack 6: Unregistered Device
    print('\n--- TEST 6: Unregistered Device Access ---')
    print('Scenario: Unknown device tries to authenticate')
    rogue = copy.copy(devices[4])
    rogue.id = 'ROGUE_DEVICE'
    rogue.registered = True
    rogue.credentials = {
        'A_device': sha256_hash('ROGUE'),
        'RPW': sha256_hash('ROGUE_RPW'),
        'C': sha256_hash('ROGUE_C'),
        'FID': fog.id,
        'r': 'rogue_nonce'
    }
    result, _, fog = device_login(rogue, fog)
    if not result['success']:
        print(f"RESULT: ATTACK BLOCKED - {result['failure_reason']}")
        passed += 1
    else:
        print('RESULT: VULNERABILITY - Rogue device accessed the system!')

    # Summary
    print('\n========== SECURITY ANALYSIS SUMMARY ==========')
    print(f"Tests passed: {passed} / {total}")
    if passed == total:
        print('STATUS: ALL ATTACKS BLOCKED SUCCESSFULLY')
    else:
        print(f"STATUS: {total - passed} VULNERABILITIES DETECTED")
    print('================================================')

if __name__ == '__main__':
    run_security_analysis()
