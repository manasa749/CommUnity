function App() {
    const [currentPage, setCurrentPage] = React.useState('dashboard');
    const [backendStatus, setBackendStatus] = React.useState({
        status: 'connecting',
        message: 'Attempting to contact backend...',
        version: '',
        database: ''
    });

    React.useEffect(() => {
        // Fetch server status to verify communication
        fetch('/api/status')
            .then(res => {
                if (!res.ok) {
                    throw new Error(`HTTP error! status: ${res.status}`);
                }
                return res.json();
            })
            .then(data => {
                setBackendStatus({
                    status: 'connected',
                    message: data.message,
                    version: data.version,
                    database: data.database
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

    const renderContent = () => {
        switch (currentPage) {
            case 'dashboard':
                return (
                    <div className="card">
                        <h2>Dashboard</h2>
                        <p className="welcome-text">Welcome to <strong>CommUnity</strong>, your central residential intelligence platform.</p>
                        
                        <div className="status-container">
                            <h3>Backend Connectivity Verification</h3>
                            <div className={`status-badge ${backendStatus.status}`}>
                                {backendStatus.status.toUpperCase()}
                            </div>
                            <div className="status-details">
                                <p><strong>Server Message:</strong> {backendStatus.message}</p>
                                <p><strong>API Version:</strong> {backendStatus.version}</p>
                                <p><strong>Database System:</strong> {backendStatus.database}</p>
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
                        <p className="info-text">Manage your personal settings, flat/villa references, and verification status.</p>
                        <div className="skeleton-item">Resident profile view placeholder...</div>
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
