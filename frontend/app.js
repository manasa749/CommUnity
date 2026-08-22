function App() {
    // Auth and Navigation State
    const [token, setToken] = React.useState(localStorage.getItem('token') || null);
    const [user, setUser] = React.useState(null);
    const [loading, setLoading] = React.useState(!!token);
    const [currentPage, setCurrentPage] = React.useState(token ? 'dashboard' : 'login');
    
    // Status connection state
    const [backendStatus, setBackendStatus] = React.useState({
        status: 'connecting',
        message: 'Attempting to contact backend...',
        version: '',
        database: ''
    });

    // Form inputs state - Login
    const [loginEmail, setLoginEmail] = React.useState('');
    const [loginPassword, setLoginPassword] = React.useState('');
    const [loginError, setLoginError] = React.useState('');
    const [loginSuccess, setLoginSuccess] = React.useState('');

    // Form inputs state - Signup
    const [signupName, setSignupName] = React.useState('');
    const [signupEmail, setSignupEmail] = React.useState('');
    const [signupFlat, setSignupFlat] = React.useState('');
    const [signupPassword, setSignupPassword] = React.useState('');
    const [signupConfirmPassword, setSignupConfirmPassword] = React.useState('');
    const [signupError, setSignupError] = React.useState('');
    const [signupSuccess, setSignupSuccess] = React.useState('');

    // Check backend connection on boot
    React.useEffect(() => {
        fetch('/api/status')
            .then(res => {
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                return res.json();
            })
            .then(data => {
                setBackendStatus({
                    status: 'connected',
                    message: data.message,
                    version: data.version,
                    database: data.database_file || 'SQLite'
                });
            })
            .catch(err => {
                setBackendStatus({
                    status: 'error',
                    message: `Failed to connect to backend: ${err.message}`,
                    version: 'N/A',
                    database: 'N/A'
                });
            });
    }, []);

    // Fetch user profile whenever token changes
    React.useEffect(() => {
        if (token) {
            setLoading(true);
            fetch('/api/auth/me', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })
            .then(res => {
                if (!res.ok) throw new Error('Unauthorized');
                return res.json();
            })
            .then(profile => {
                setUser(profile);
                setLoading(false);
            })
            .catch(() => {
                // Token invalid or expired
                localStorage.removeItem('token');
                setToken(null);
                setUser(null);
                setCurrentPage('login');
                setLoading(false);
            });
        } else {
            setUser(null);
            setLoading(false);
        }
    }, [token]);

    // Handle Login submission
    const handleLogin = (e) => {
        e.preventDefault();
        setLoginError('');

        if (!loginEmail.trim() || !loginPassword) {
            setLoginError('Please enter both email and password.');
            return;
        }

        fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: loginEmail, password: loginPassword })
        })
        .then(async res => {
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.detail || 'Login failed');
            }
            return data;
        })
        .then(data => {
            localStorage.setItem('token', data.access_token);
            setToken(data.access_token);
            setLoginEmail('');
            setLoginPassword('');
            setCurrentPage('dashboard');
        })
        .catch(err => {
            setLoginError(err.message);
        });
    };

    // Handle Signup submission
    const handleSignup = (e) => {
        e.preventDefault();
        setSignupError('');
        setSignupSuccess('');

        // Basic frontend input validation
        if (!signupName.trim() || !signupEmail.trim() || !signupFlat.trim() || !signupPassword || !signupConfirmPassword) {
            setSignupError('All fields are required.');
            return;
        }

        if (signupPassword !== signupConfirmPassword) {
            setSignupError('Passwords do not match.');
            return;
        }

        if (signupPassword.length < 6) {
            setSignupError('Password must be at least 6 characters.');
            return;
        }

        fetch('/api/auth/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: signupName,
                email: signupEmail,
                flat_number: signupFlat,
                password: signupPassword,
                confirm_password: signupConfirmPassword
            })
        })
        .then(async res => {
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.detail || 'Registration failed');
            }
            return data;
        })
        .then(() => {
            setLoginSuccess('Account registered successfully! Please log in.');
            setSignupName('');
            setSignupEmail('');
            setSignupFlat('');
            setSignupPassword('');
            setSignupConfirmPassword('');
            setCurrentPage('login');
        })
        .catch(err => {
            setSignupError(err.message);
        });
    };

    // Handle Logout
    const handleLogout = () => {
        localStorage.removeItem('token');
        setToken(null);
        setUser(null);
        setCurrentPage('login');
    };

    // Router and layout controller
    const renderContent = () => {
        if (loading) {
            return (
                <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
                    <p>Loading your profile details...</p>
                </div>
            );
        }

        // Redirect unauthenticated users to login or signup
        if (!user) {
            if (currentPage === 'signup') {
                return (
                    <div className="card">
                        <h2>Create CommUnity Account</h2>
                        <p className="welcome-text">Join your residential community intelligence portal.</p>
                        
                        {signupError && <div className="error-panel">{signupError}</div>}
                        {signupSuccess && <div className="success-panel">{signupSuccess}</div>}

                        <form onSubmit={handleSignup}>
                            <div className="form-group">
                                <label>Full Name</label>
                                <input 
                                    type="text" 
                                    value={signupName} 
                                    onChange={e => setSignupName(e.target.value)} 
                                    placeholder="Enter your full name"
                                />
                            </div>
                            <div className="form-group">
                                <label>Email Address</label>
                                <input 
                                    type="email" 
                                    value={signupEmail} 
                                    onChange={e => setSignupEmail(e.target.value)} 
                                    placeholder="name@example.com"
                                />
                            </div>
                            <div className="form-group">
                                <label>Flat / Unit Number</label>
                                <input 
                                    type="text" 
                                    value={signupFlat} 
                                    onChange={e => setSignupFlat(e.target.value)} 
                                    placeholder="e.g. Block A - 402"
                                />
                            </div>
                            <div className="form-group">
                                <label>Password</label>
                                <input 
                                    type="password" 
                                    value={signupPassword} 
                                    onChange={e => setSignupPassword(e.target.value)} 
                                    placeholder="Minimum 6 characters"
                                />
                            </div>
                            <div className="form-group">
                                <label>Confirm Password</label>
                                <input 
                                    type="password" 
                                    value={signupConfirmPassword} 
                                    onChange={e => setSignupConfirmPassword(e.target.value)} 
                                    placeholder="Re-enter password"
                                />
                            </div>
                            <button type="submit" className="btn-primary">Register Resident</button>
                        </form>

                        <div className="auth-switch">
                            Already have an account?{' '}
                            <button className="btn-secondary" onClick={() => { setSignupError(''); setSignupSuccess(''); setCurrentPage('login'); }}>
                                Log In
                            </button>
                        </div>
                    </div>
                );
            }

            // Default fallback: login view
            return (
                <div className="card">
                    <h2>CommUnity Login</h2>
                    <p className="welcome-text">Log in to interact with your neighborhood portal.</p>
                    
                    {loginSuccess && <div className="success-panel">{loginSuccess}</div>}
                    {loginError && <div className="error-panel">{loginError}</div>}

                    <form onSubmit={handleLogin}>
                        <div className="form-group">
                            <label>Email Address</label>
                            <input 
                                type="email" 
                                value={loginEmail} 
                                onChange={e => setLoginEmail(e.target.value)} 
                                placeholder="name@example.com"
                            />
                        </div>
                        <div className="form-group">
                            <label>Password</label>
                            <input 
                                type="password" 
                                value={loginPassword} 
                                onChange={e => setLoginPassword(e.target.value)} 
                                placeholder="Enter password"
                            />
                        </div>
                        <button type="submit" className="btn-primary">Log In</button>
                    </form>

                    <div className="auth-switch">
                        New resident?{' '}
                        <button className="btn-secondary" onClick={() => { setLoginError(''); setLoginSuccess(''); setCurrentPage('signup'); }}>
                            Create an account
                        </button>
                    </div>
                </div>
            );
        }

        // Authenticated Views
        switch (currentPage) {
            case 'dashboard':
                return (
                    <div className="card">
                        <h2>Dashboard</h2>
                        <p className="welcome-text">Welcome back, <strong>{user.name}</strong>!</p>
                        
                        <div className="status-container">
                            <h3>Backend Connectivity Status</h3>
                            <div className={`status-badge ${backendStatus.status}`}>
                                {backendStatus.status.toUpperCase()}
                            </div>
                            <div className="status-details">
                                <p><strong>Server Message:</strong> {backendStatus.message}</p>
                                <p><strong>API Version:</strong> {backendStatus.version}</p>
                                <p><strong>Connected Database:</strong> {backendStatus.database}</p>
                            </div>
                        </div>
                    </div>
                );
            case 'contacts':
                return (
                    <div className="card">
                        <h2>Community Contacts</h2>
                        <p className="info-text">Important emergency numbers, security personnel, and community management details will be listed here.</p>
                        <div className="skeleton-item">Directory loading mechanism placeholder...</div>
                    </div>
                );
            case 'recommendations':
                return (
                    <div className="card">
                        <h2>Trusted Recommendations</h2>
                        <p className="info-text">Discover, search, and share trusted local service providers recommended by your neighbors.</p>
                        <div className="skeleton-item">Recommendation list loading placeholder...</div>
                    </div>
                );
            case 'issues':
                return (
                    <div className="card">
                        <h2>Community Issues</h2>
                        <p className="info-text">Report and track maintenance, security, or utility issues in the community transparently.</p>
                        <div className="skeleton-item">Issue tracker board placeholder...</div>
                    </div>
                );
            case 'profile':
                return (
                    <div className="card">
                        <h2>Resident Profile</h2>
                        <p className="info-text">View your account profile, unit configuration, and role status.</p>
                        
                        <div className="profile-info">
                            <div className="profile-field">
                                <strong>Resident Name</strong>
                                <span>{user.name}</span>
                            </div>
                            <div className="profile-field">
                                <strong>Email Address</strong>
                                <span>{user.email}</span>
                            </div>
                            <div className="profile-field">
                                <strong>Flat / Unit Number</strong>
                                <span>{user.flat_number}</span>
                            </div>
                            <div className="profile-field">
                                <strong>Access Role</strong>
                                <span>{user.role}</span>
                            </div>
                        </div>

                        <button className="btn-primary btn-logout" onClick={handleLogout}>Log Out</button>
                    </div>
                );
            default:
                return <div>Page not found</div>;
        }
    };

    return (
        <div className="app-container">
            <header className="header">
                <div className="logo-container">
                    <span className="logo-icon">🏘️</span>
                    <span className="logo-text">CommUnity</span>
                </div>
                
                {user && (
                    <nav className="nav">
                        <button 
                            className={`nav-link ${currentPage === 'dashboard' ? 'active' : ''}`}
                            onClick={() => setCurrentPage('dashboard')}
                        >
                            Dashboard
                        </button>
                        <button 
                            className={`nav-link ${currentPage === 'contacts' ? 'active' : ''}`}
                            onClick={() => setCurrentPage('contacts')}
                        >
                            Contacts
                        </button>
                        <button 
                            className={`nav-link ${currentPage === 'recommendations' ? 'active' : ''}`}
                            onClick={() => setCurrentPage('recommendations')}
                        >
                            Recommendations
                        </button>
                        <button 
                            className={`nav-link ${currentPage === 'issues' ? 'active' : ''}`}
                            onClick={() => setCurrentPage('issues')}
                        >
                            Issues
                        </button>
                        <button 
                            className={`nav-link ${currentPage === 'profile' ? 'active' : ''}`}
                            onClick={() => setCurrentPage('profile')}
                        >
                            Profile
                        </button>
                    </nav>
                )}
                
                {user && (
                    <div className="user-meta">
                        <span className="user-name">📍 Unit {user.flat_number}</span>
                    </div>
                )}
            </header>
            
            <main className="main-content">
                {renderContent()}
            </main>
            
            <footer className="footer">
                <p>&copy; 2026 CommUnity Platform. All rights reserved.</p>
            </footer>
        </div>
    );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
