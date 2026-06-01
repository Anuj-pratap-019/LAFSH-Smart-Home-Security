import time
import numpy as np
from init import init_cloud, init_fog_node, init_rbac
from network import deploy_nodes
from auth import device_register, device_login

def eval_auth_latency(num_devices_range=None, num_trials=5):
    """Measure authentication latency vs number of devices."""
    if num_devices_range is None:
        num_devices_range = [50, 100, 200, 300, 500]

    results = {
        'num_devices': num_devices_range,
        'avg_reg_ms': [],
        'avg_auth_ms': [],
        'std_reg_ms': [],
        'std_auth_ms': []
    }

    print('\n=== Authentication Latency Evaluation ===')

    for N in num_devices_range:
        reg_times = []
        auth_times = []

        for trial in range(num_trials):
            # Fresh setup per trial
            cloud = init_cloud()
            rbac = init_rbac()
            fog = init_fog_node('FOG_EVAL', cloud, rbac)

            devices = deploy_nodes(N, 200)

            # Measure registration latency
            t0 = time.time()
            for d in devices:
                device_register(d, fog)
            reg_times.append((time.time() - t0) * 1000 / N)  # Per-device avg

            # Measure authentication latency
            t0 = time.time()
            for d in devices:
                device_login(d, fog)
            auth_times.append((time.time() - t0) * 1000 / N)  # Per-device avg

            print(f"  N={N}, trial={trial+1}: reg={reg_times[-1]:.3f} ms/dev, auth={auth_times[-1]:.3f} ms/dev")

        results['avg_reg_ms'].append(np.mean(reg_times))
        results['avg_auth_ms'].append(np.mean(auth_times))
        results['std_reg_ms'].append(np.std(reg_times, ddof=1) if len(reg_times) > 1 else 0.0)
        results['std_auth_ms'].append(np.std(auth_times, ddof=1) if len(auth_times) > 1 else 0.0)

    print('=== Evaluation complete ===\n')
    return results

def eval_communication_overhead():
    """Compare bytes exchanged per authentication."""
    print('\n=== Communication Overhead Evaluation ===')

    schemes = ['LAFSH', 'Basic-PW', 'DTLS-PSK', 'TLS-Cert']
    registration_bytes = np.array([150, 80, 200, 4000])
    authentication_bytes = np.array([200, 100, 500, 5000])
    totp_bytes = np.array([20, 0, 0, 0])
    total_bytes = registration_bytes + authentication_bytes + totp_bytes

    results = {
        'schemes': schemes,
        'registration_bytes': registration_bytes.tolist(),
        'authentication_bytes': authentication_bytes.tolist(),
        'totp_bytes': totp_bytes.tolist(),
        'total_bytes': total_bytes.tolist()
    }

    # Print comparison table
    print(f"\n{'Scheme':<12}  {'Reg(B)':>8}  {'Auth(B)':>8}  {'TOTP(B)':>8}  {'Total(B)':>8}")
    print('-' * 52)
    for i in range(len(schemes)):
        print(f"{schemes[i]:<12}  {registration_bytes[i]:>8}  {authentication_bytes[i]:>8}  {totp_bytes[i]:>8}  {total_bytes[i]:>8}")
    
    efficiency = total_bytes[3] / total_bytes[0]
    print(f"\nLAFSH is {efficiency:.1f}x more efficient than TLS-Cert\n")
    return results

def eval_energy_estimation(num_devices_range=None):
    """Estimate energy consumption for authentication."""
    if num_devices_range is None:
        num_devices_range = [50, 100, 200, 300, 500]
    num_devices_range = np.array(num_devices_range)

    print('\n=== Energy Consumption Estimation ===')

    # Energy constants (microjoules)
    E_hash = 0.3       # SHA-256
    E_xor = 0.001      # 256-bit XOR
    E_tx_byte = 0.5    # BLE transmission per byte
    E_rx_byte = 0.3    # BLE reception per byte
    E_rsa = 900000.0   # RSA-2048 signing

    # LAFSH per device: 8 hashes, 2 XORs, 200 bytes TX, 200 bytes RX
    lafsh_comp = 8 * E_hash + 2 * E_xor
    lafsh_comm = 200 * E_tx_byte + 200 * E_rx_byte
    lafsh_total = lafsh_comp + lafsh_comm

    # PKI per device: 2 RSA, ~3500 bytes TX/RX
    pki_comp = 2 * E_rsa
    pki_comm = 3500 * E_tx_byte + 3500 * E_rx_byte
    pki_total = pki_comp + pki_comm

    # TLS per device: 1 RSA + AES, ~5000 bytes
    tls_comp = E_rsa + 50.0  # RSA + AES overhead
    tls_comm = 5000 * E_tx_byte + 5000 * E_rx_byte
    tls_total = tls_comp + tls_comm

    results = {
        'num_devices': num_devices_range.tolist(),
        'lafsh_per_device': lafsh_total,
        'pki_per_device': pki_total,
        'tls_per_device': tls_total,
        'lafsh_total': (lafsh_total * num_devices_range).tolist(),
        'pki_total': (pki_total * num_devices_range).tolist(),
        'tls_total': (tls_total * num_devices_range).tolist(),
        'lafsh_breakdown': [lafsh_comp, lafsh_comm],
        'pki_breakdown': [pki_comp, pki_comm]
    }

    print('\nPer-device energy (microjoules):')
    print(f"  LAFSH:    {lafsh_total:.2f} uJ (comp={lafsh_comp:.2f}, comm={lafsh_comm:.2f})")
    print(f"  TLS:      {tls_total:.2f} uJ")
    print(f"  PKI:      {pki_total:.2f} uJ")
    
    efficiency = pki_total / lafsh_total
    print(f"\nLAFSH is {efficiency:.0f}x more energy-efficient than PKI\n")
    return results

def eval_security_comparison():
    """Security feature comparison across schemes."""
    print('\n=== Security Feature Comparison ===')

    schemes = ['LAFSH', 'Basic-PW', 'TLS', 'Wazid2020']
    features = [
        'Mutual Auth', 'Replay Protection', 'MITM Resistance',
        'Device Fingerprint', 'Two-Factor Auth', 'Forward Secrecy',
        'Computation Cost', 'Communication Cost'
    ]

    # Scores: [LAFSH, Basic-PW, TLS, Wazid2020]
    scores = np.array([
        [3, 0, 2, 3],   # Mutual Auth
        [3, 0, 3, 3],   # Replay Protection
        [3, 1, 3, 3],   # MITM Resistance
        [3, 0, 0, 1],   # Device Fingerprint
        [3, 0, 0, 0],   # Two-Factor Auth
        [2, 0, 3, 2],   # Forward Secrecy
        [3, 3, 1, 3],   # Computation Cost (3=low cost = good)
        [3, 2, 0, 2]    # Communication Cost (3=low cost = good)
    ])

    results = {
        'schemes': schemes,
        'features': features,
        'scores': scores.tolist(),
        'totals': scores.sum(axis=0).tolist()
    }

    # Print table
    print(f"\n{'Feature':<22}", end="")
    for s in schemes:
        print(f" {s:>10}", end="")
    print()
    print('-' * 66)

    labels = ['None', 'Partial', 'Good', 'Full']
    for f in range(len(features)):
        print(f"{features[f]:<22}", end="")
        for s in range(len(schemes)):
            score = scores[f, s]
            print(f" {labels[score]:>10}", end="")
        print()

    print('-' * 66)
    print(f"{'TOTAL (out of 24)':<22}", end="")
    totals = results['totals']
    for s in range(len(schemes)):
        print(f" {totals[s]:>10d}", end="")
    print()
    return results
