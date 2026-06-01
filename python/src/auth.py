import time
from utils import get_timestamp, generate_nonce, sha256_hash, totp_verify, totp_generate

def device_register(device, fog):
    """Execute the device registration protocol (Phase 1)."""
    start_time = time.time()
    
    DID = device.id
    PW = device.password

    # Device side
    r = generate_nonce(128)  # 16-byte registration nonce
    RPW = sha256_hash(f"{DID}||{PW}||{r}")
    fp = device.fingerprint

    # Registration request size (bytes)
    reg_request_bytes = len(DID) + 32 + 16 + 32 + len(device.role)

    # Fog side
    if DID in fog.device_registry:
        reg_stats = {
            'success': False,
            'reason': 'Device already registered',
            'latency_ms': (time.time() - start_time) * 1000
        }
        return device, fog, reg_stats

    # Compute anchor key
    A = sha256_hash(f"{DID}||{fog.secret}")

    # Compute credential certificate
    C = sha256_hash(f"{DID}||{A}||{fp}")

    # Generate TOTP secret for user-role devices
    totp_secret = ''
    if device.role in ('Admin', 'Resident'):
        totp_secret = generate_nonce(128)

    # Store in fog registry
    record = {
        'anchor_key': A,
        'credential': C,
        'role': device.role,
        'fingerprint': fp,
        'totp_secret': totp_secret,
        'registered_at': get_timestamp(),
        'device_type': device.type
    }
    fog.device_registry[DID] = record

    # Registration response size (bytes)
    reg_response_bytes = 32 + len(fog.id)

    # Device stores credentials
    device.credentials = {
        'RPW': RPW,
        'C': C,
        'FID': fog.id,
        'r': r,
        'A_device': A
    }
    device.totp_secret = totp_secret
    device.registered = True

    # Log in fog audit log
    fog.audit_log.append({
        'timestamp': get_timestamp(),
        'event': 'REGISTRATION',
        'device_id': DID,
        'role': device.role,
        'status': 'SUCCESS'
    })

    latency = (time.time() - start_time) * 1000

    reg_stats = {
        'success': True,
        'reason': 'Registration successful',
        'latency_ms': latency,
        'bytes_exchanged': reg_request_bytes + reg_response_bytes,
        'hash_operations': 3,
        'totp_enabled': bool(totp_secret)
    }

    print(f"[REG] Device {DID} ({device.type}, role={device.role}) registered successfully ({latency:.2f} ms)")
    return device, fog, reg_stats

def device_login(device, fog, sim_time=None):
    """Mutual authentication + session key establishment (Phase 2)."""
    start_time = time.time()
    
    if sim_time is None:
        sim_time = get_timestamp()

    DID = device.id
    auth_result = {}

    # Precondition check
    if not device.registered:
        auth_result = {
            'success': False,
            'failure_reason': 'Device not registered',
            'latency_ms': (time.time() - start_time) * 1000
        }
        return auth_result, device, fog

    # DEVICE SIDE (Step D1-D2)
    A_device = device.credentials['A_device']
    N1 = generate_nonce(128)
    T1 = str(sim_time)

    Auth1 = sha256_hash(f"{DID}||{A_device}||{N1}||{T1}")

    # M1 message properties
    m1_bytes = len(DID) + 32 + 16 + 4 + 32  # ~100 bytes

    # FOG SIDE (Step F1-F6)
    current_time = get_timestamp()
    time_diff = abs(current_time - int(T1))

    if time_diff > fog.clock_delta:
        auth_result = {
            'success': False,
            'failure_reason': f"Timestamp expired (diff={time_diff}s, delta={fog.clock_delta}s)",
            'latency_ms': (time.time() - start_time) * 1000,
            'bytes_exchanged': m1_bytes
        }
        fog.audit_log.append({
            'timestamp': current_time,
            'event': 'AUTH_FAIL',
            'device_id': DID,
            'reason': 'TIMESTAMP_EXPIRED',
            'status': 'BLOCKED'
        })
        print(f"[AUTH] FAILED: {DID} - Timestamp expired")
        return auth_result, device, fog

    if DID not in fog.device_registry:
        auth_result = {
            'success': False,
            'failure_reason': 'Device not found in registry',
            'latency_ms': (time.time() - start_time) * 1000,
            'bytes_exchanged': m1_bytes
        }
        print(f"[AUTH] FAILED: {DID} - Not in registry")
        return auth_result, device, fog

    record = fog.device_registry[DID]

    # Fingerprint verification (device cloning detection)
    if device.fingerprint != record['fingerprint']:
        auth_result = {
            'success': False,
            'failure_reason': 'DEVICE CLONING DETECTED - fingerprint mismatch',
            'latency_ms': (time.time() - start_time) * 1000,
            'bytes_exchanged': m1_bytes
        }
        fog.audit_log.append({
            'timestamp': current_time,
            'event': 'SECURITY_ALERT',
            'device_id': DID,
            'reason': 'DEVICE_CLONING',
            'status': 'BLOCKED'
        })
        print(f"[AUTH] ALERT: {DID} - Device cloning detected!")
        return auth_result, device, fog

    # Verify Auth1
    A = record['anchor_key']
    Auth1_expected = sha256_hash(f"{DID}||{A}||{N1}||{T1}")

    if Auth1 != Auth1_expected:
        auth_result = {
            'success': False,
            'failure_reason': 'Auth1 verification failed - invalid credentials',
            'latency_ms': (time.time() - start_time) * 1000,
            'bytes_exchanged': m1_bytes
        }
        
        # Track failed attempts
        fog.failed_attempts[DID] = fog.failed_attempts.get(DID, 0) + 1
        
        fog.audit_log.append({
            'timestamp': current_time,
            'event': 'AUTH_FAIL',
            'device_id': DID,
            'reason': 'INVALID_CREDENTIALS',
            'status': 'BLOCKED'
        })
        print(f"[AUTH] FAILED: {DID} - Invalid credentials")
        return auth_result, device, fog

    # Fog computes Auth2
    N2 = generate_nonce(128)
    T2 = str(sim_time + 1)
    Auth2 = sha256_hash(f"{fog.id}||{A}||{N1}||{N2}||{T2}")

    # Session Key SK
    SK = sha256_hash(f"{N1}||{N2}||{A}||{DID}||{fog.id}")
    SK_hash = sha256_hash(SK)

    m2_bytes = len(fog.id) + 16 + 4 + 32 + 32  # ~100 bytes

    # DEVICE SIDE (Step D3-D4)
    Auth2_expected = sha256_hash(f"{fog.id}||{A_device}||{N1}||{N2}||{T2}")

    if Auth2 != Auth2_expected:
        auth_result = {
            'success': False,
            'failure_reason': 'Auth2 verification failed - fog node impersonation',
            'latency_ms': (time.time() - start_time) * 1000,
            'bytes_exchanged': m1_bytes + m2_bytes
        }
        print(f"[AUTH] FAILED: {DID} - Fog impersonation detected")
        return auth_result, device, fog

    SK_device = sha256_hash(f"{N1}||{N2}||{A_device}||{DID}||{fog.id}")

    if sha256_hash(SK_device) != SK_hash:
        auth_result = {
            'success': False,
            'failure_reason': 'Session key mismatch',
            'latency_ms': (time.time() - start_time) * 1000,
            'bytes_exchanged': m1_bytes + m2_bytes
        }
        return auth_result, device, fog

    # Store active session on Fog
    session = {
        'session_key': SK,
        'created_at': current_time,
        'expires_at': current_time + fog.session_timeout,
        'role': record['role'],
        'device_type': record['device_type'],
        'totp_verified': False
    }
    fog.active_sessions[DID] = session

    device.authenticated = True
    device.session_key = SK_device

    # Reset failed attempts
    fog.failed_attempts[DID] = 0

    fog.audit_log.append({
        'timestamp': current_time,
        'event': 'AUTH_SUCCESS',
        'device_id': DID,
        'role': record['role'],
        'status': 'SUCCESS'
    })

    latency = (time.time() - start_time) * 1000

    auth_result = {
        'success': True,
        'session_key': SK_device,
        'failure_reason': '',
        'latency_ms': latency,
        'bytes_exchanged': m1_bytes + m2_bytes,
        'hash_operations': 8,
        'needs_totp': record['role'] in ('Admin', 'Resident')
    }

    print(f"[AUTH] SUCCESS: {DID} ({record['role']}) mutually authenticated ({latency:.2f} ms, {m1_bytes + m2_bytes} bytes)")
    return auth_result, device, fog

def totp_auth(device, fog, submitted_otp, sim_time=None):
    """Two-Factor Authentication via TOTP (Phase 3)."""
    start_time = time.time()
    
    if sim_time is None:
        sim_time = get_timestamp()

    DID = device.id
    totp_result = {}

    if DID not in fog.active_sessions:
        totp_result = {
            'success': False,
            'reason': 'No active session - authenticate first',
            'latency_ms': (time.time() - start_time) * 1000
        }
        return totp_result, fog

    session = fog.active_sessions[DID]

    if session['role'] not in ('Admin', 'Resident'):
        totp_result = {
            'success': True,
            'reason': 'TOTP not required for this role',
            'latency_ms': (time.time() - start_time) * 1000
        }
        return totp_result, fog

    record = fog.device_registry[DID]

    if not record['totp_secret']:
        totp_result = {
            'success': False,
            'reason': 'No TOTP secret configured',
            'latency_ms': (time.time() - start_time) * 1000
        }
        return totp_result, fog

    valid = totp_verify(record['totp_secret'], submitted_otp, sim_time)

    if valid:
        session['totp_verified'] = True
        fog.active_sessions[DID] = session

        fog.audit_log.append({
            'timestamp': sim_time,
            'event': 'TOTP_SUCCESS',
            'device_id': DID,
            'role': session['role'],
            'status': 'SUCCESS'
        })

        totp_result = {
            'success': True,
            'reason': 'TOTP verified successfully'
        }
        print(f"[2FA] SUCCESS: {DID} ({session['role']}) TOTP verified")
    else:
        fog.audit_log.append({
            'timestamp': sim_time,
            'event': 'TOTP_FAIL',
            'device_id': DID,
            'role': session['role'],
            'status': 'BLOCKED'
        })

        totp_result = {
            'success': False,
            'reason': 'Invalid TOTP code'
        }
        print(f"[2FA] FAILED: {DID} - Invalid TOTP code")

    totp_result['latency_ms'] = (time.time() - start_time) * 1000
    totp_result['expected_otp'] = totp_generate(record['totp_secret'], sim_time)
    
    return totp_result, fog

def verify_session(device_id, fog, current_time=None):
    """Check if a device has a valid, non-expired session."""
    if current_time is None:
        current_time = get_timestamp()

    if device_id not in fog.active_sessions:
        return False

    session = fog.active_sessions[device_id]

    if current_time > session['expires_at']:
        # Session expired, clean up
        del fog.active_sessions[device_id]
        return False

    return True

def logout_device(device_id, fog):
    """Invalidate a device session."""
    if device_id in fog.active_sessions:
        del fog.active_sessions[device_id]
        fog.audit_log.append({
            'timestamp': get_timestamp(),
            'event': 'LOGOUT',
            'device_id': device_id,
            'reason': 'USER_INITIATED',
            'status': 'SUCCESS'
        })
        print(f"[SESSION] Device {device_id} logged out")
    else:
        print(f"[SESSION] Device {device_id} has no active session")
    return fog
