// ─── Constants ────────────────────────────────────────────────────────────────

const CONTACT_CATEGORIES = ["All", "Management", "Maintenance", "Security", "Emergency", "Other"];

const REC_CATEGORIES = [
    "All", "Broadband", "Plumber", "Electrician", "AC Service",
    "Appliance Repair", "Cleaning", "Tutor", "Healthcare", "Laundry", "Other"
];

// ─── API helpers ──────────────────────────────────────────────────────────────

function apiFetch(path, token, options = {}) {
    return fetch(path, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(token ? { "Authorization": `Bearer ${token}` } : {}),
            ...(options.headers || {})
        }
    }).then(async res => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Request failed");
        return data;
    });
}

// ─── Contacts Page ────────────────────────────────────────────────────────────

function ContactsPage({ token }) {
    const [contacts, setContacts] = React.useState([]);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState("");
    const [search, setSearch] = React.useState("");
    const [category, setCategory] = React.useState("All");
    const [selected, setSelected] = React.useState(null);

    const fetchContacts = (cat, q) => {
        setLoading(true);
        setError("");
        const params = new URLSearchParams();
        if (cat && cat !== "All") params.append("category", cat);
        if (q && q.trim()) params.append("search", q.trim());
        apiFetch(`/api/contacts?${params.toString()}`, token)
            .then(data => { setContacts(data); setLoading(false); })
            .catch(err => { setError(err.message); setLoading(false); });
    };

    React.useEffect(() => { fetchContacts("All", ""); }, []);

    const handleSearch = (e) => {
        e.preventDefault();
        fetchContacts(category, search);
    };

    const handleCategoryChange = (cat) => {
        setCategory(cat);
        fetchContacts(cat, search);
    };

    if (selected) {
        return (
            <div className="card">
                <button className="btn-back" onClick={() => setSelected(null)}>← Back to Contacts</button>
                <h2>{selected.name}</h2>
                <span className={`category-badge cat-${selected.category.toLowerCase()}`}>{selected.category}</span>
                <div className="detail-grid">
                    <div className="detail-row"><strong>Designation</strong><span>{selected.designation}</span></div>
                    {selected.phone    && <div className="detail-row"><strong>Phone</strong><span>{selected.phone}</span></div>}
                    {selected.email    && <div className="detail-row"><strong>Email</strong><span>{selected.email}</span></div>}
                    {selected.availability && <div className="detail-row"><strong>Availability</strong><span>{selected.availability}</span></div>}
                </div>
            </div>
        );
    }

    return (
        <div className="card">
            <h2>Community Contacts</h2>
            <p className="info-text">Find emergency numbers, management, maintenance, and security contacts for your community.</p>

            <form onSubmit={handleSearch} className="search-bar">
                <input
                    type="text"
                    placeholder="Search contacts..."
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                />
                <button type="submit" className="btn-primary btn-sm">Search</button>
            </form>

            <div className="filter-tabs">
                {CONTACT_CATEGORIES.map(cat => (
                    <button
                        key={cat}
                        className={`filter-tab ${category === cat ? "active" : ""}`}
                        onClick={() => handleCategoryChange(cat)}
                    >{cat}</button>
                ))}
            </div>

            {loading && <p className="loading-text">Loading contacts...</p>}
            {error   && <div className="error-panel">{error}</div>}

            {!loading && !error && contacts.length === 0 && (
                <div className="empty-state">No contacts found for your search.</div>
            )}

            {!loading && contacts.length > 0 && (
                <div className="list">
                    {contacts.map(c => (
                        <div key={c.id} className="list-item" onClick={() => setSelected(c)}>
                            <div className="list-item-main">
                                <span className="list-item-title">{c.name}</span>
                                <span className="list-item-sub">{c.designation}</span>
                            </div>
                            <div className="list-item-right">
                                <span className={`category-badge cat-${c.category.toLowerCase()}`}>{c.category}</span>
                                {c.phone && <span className="contact-phone">{c.phone}</span>}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

// ─── Add Recommendation Form ──────────────────────────────────────────────────

function AddRecommendationForm({ token, onAdded, onCancel }) {
    const [serviceName, setServiceName] = React.useState("");
    const [category, setCategory] = React.useState("Plumber");
    const [description, setDescription] = React.useState("");
    const [contactInfo, setContactInfo] = React.useState("");
    const [error, setError] = React.useState("");
    const [saving, setSaving] = React.useState(false);

    const handleSubmit = (e) => {
        e.preventDefault();
        setError("");
        if (!serviceName.trim() || !description.trim()) {
            setError("Service name and description are required.");
            return;
        }
        setSaving(true);
        apiFetch("/api/recommendations", token, {
            method: "POST",
            body: JSON.stringify({ service_name: serviceName, category, description, contact_info: contactInfo })
        })
        .then(rec => { setSaving(false); onAdded(rec); })
        .catch(err => { setError(err.message); setSaving(false); });
    };

    return (
        <div className="card">
            <button className="btn-back" onClick={onCancel}>← Back to Recommendations</button>
            <h2>Add a Recommendation</h2>
            <p className="info-text">Share a trusted service provider with your neighbours.</p>

            {error && <div className="error-panel">{error}</div>}

            <form onSubmit={handleSubmit}>
                <div className="form-group">
                    <label>Service / Provider Name</label>
                    <input type="text" value={serviceName} onChange={e => setServiceName(e.target.value)} placeholder="e.g. Rajan Plumbing" />
                </div>
                <div className="form-group">
                    <label>Category</label>
                    <select value={category} onChange={e => setCategory(e.target.value)} className="form-select">
                        {REC_CATEGORIES.filter(c => c !== "All").map(c => (
                            <option key={c} value={c}>{c}</option>
                        ))}
                    </select>
                </div>
                <div className="form-group">
                    <label>Description</label>
                    <textarea
                        value={description}
                        onChange={e => setDescription(e.target.value)}
                        placeholder="Describe the service and why you recommend it..."
                        rows="4"
                        className="form-textarea"
                    />
                </div>
                <div className="form-group">
                    <label>Contact Information <span className="label-optional">(optional)</span></label>
                    <input type="text" value={contactInfo} onChange={e => setContactInfo(e.target.value)} placeholder="e.g. phone number or address" />
                </div>
                <button type="submit" className="btn-primary" disabled={saving}>
                    {saving ? "Saving..." : "Submit Recommendation"}
                </button>
            </form>
        </div>
    );
}

// ─── Recommendations Page ─────────────────────────────────────────────────────

function RecommendationsPage({ token }) {
    const [view, setView] = React.useState("list"); // "list" | "add" | "detail"
    const [recs, setRecs] = React.useState([]);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState("");
    const [search, setSearch] = React.useState("");
    const [category, setCategory] = React.useState("All");
    const [selected, setSelected] = React.useState(null);
    const [voteMsg, setVoteMsg] = React.useState("");

    const fetchRecs = (cat, q) => {
        setLoading(true);
        setError("");
        const params = new URLSearchParams();
        if (cat && cat !== "All") params.append("category", cat);
        if (q && q.trim()) params.append("search", q.trim());
        apiFetch(`/api/recommendations?${params.toString()}`, token)
            .then(data => { setRecs(data); setLoading(false); })
            .catch(err => { setError(err.message); setLoading(false); });
    };

    React.useEffect(() => { fetchRecs("All", ""); }, []);

    const handleSearch = (e) => {
        e.preventDefault();
        fetchRecs(category, search);
    };

    const handleCategoryChange = (cat) => {
        setCategory(cat);
        fetchRecs(cat, search);
    };

    const handleVote = (rec) => {
        setVoteMsg("");
        apiFetch(`/api/recommendations/${rec.id}/vote`, token, { method: "POST" })
            .then(updated => {
                setRecs(prev => prev.map(r => r.id === updated.id ? updated : r));
                if (selected && selected.id === updated.id) setSelected(updated);
            })
            .catch(err => { setVoteMsg(err.message); });
    };

    const handleAdded = (newRec) => {
        setView("list");
        fetchRecs(category, search);
    };

    if (view === "add") {
        return <AddRecommendationForm token={token} onAdded={handleAdded} onCancel={() => setView("list")} />;
    }

    if (view === "detail" && selected) {
        return (
            <div className="card">
                <button className="btn-back" onClick={() => { setView("list"); setSelected(null); setVoteMsg(""); }}>← Back to Recommendations</button>
                <div className="rec-detail-header">
                    <div>
                        <h2>{selected.service_name}</h2>
                        <span className={`category-badge cat-${selected.category.toLowerCase().replace(" ", "-")}`}>{selected.category}</span>
                    </div>
                    <div className="vote-block">
                        <span className="vote-count">{selected.vote_count}</span>
                        <span className="vote-label">votes</span>
                        <button
                            className={`btn-vote ${selected.user_has_voted ? "voted" : ""}`}
                            onClick={() => !selected.user_has_voted && handleVote(selected)}
                            disabled={selected.user_has_voted}
                        >
                            {selected.user_has_voted ? "✓ Voted" : "▲ Upvote"}
                        </button>
                    </div>
                </div>

                {voteMsg && <div className="error-panel">{voteMsg}</div>}

                <div className="detail-grid">
                    <div className="detail-row detail-description">
                        <strong>About</strong>
                        <span>{selected.description}</span>
                    </div>
                    {selected.contact_info && (
                        <div className="detail-row"><strong>Contact</strong><span>{selected.contact_info}</span></div>
                    )}
                    <div className="detail-row"><strong>Recommended by</strong><span>{selected.created_by_name}</span></div>
                    <div className="detail-row"><strong>Date added</strong><span>{selected.created_date}</span></div>
                </div>
            </div>
        );
    }

    // List view
    return (
        <div className="card">
            <div className="section-header">
                <h2>Trusted Recommendations</h2>
                <button className="btn-primary btn-sm" onClick={() => setView("add")}>+ Add</button>
            </div>
            <p className="info-text">Browse service recommendations shared by your neighbours, sorted by community votes.</p>

            <form onSubmit={handleSearch} className="search-bar">
                <input
                    type="text"
                    placeholder="Search recommendations..."
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                />
                <button type="submit" className="btn-primary btn-sm">Search</button>
            </form>

            <div className="filter-tabs">
                {REC_CATEGORIES.map(cat => (
                    <button
                        key={cat}
                        className={`filter-tab ${category === cat ? "active" : ""}`}
                        onClick={() => handleCategoryChange(cat)}
                    >{cat}</button>
                ))}
            </div>

            {loading && <p className="loading-text">Loading recommendations...</p>}
            {error   && <div className="error-panel">{error}</div>}

            {!loading && !error && recs.length === 0 && (
                <div className="empty-state">No recommendations found. Be the first to add one!</div>
            )}

            {!loading && recs.length > 0 && (
                <div className="list">
                    {recs.map(r => (
                        <div key={r.id} className="list-item rec-list-item">
                            <div className="list-item-main" onClick={() => { setSelected(r); setView("detail"); setVoteMsg(""); }}>
                                <span className="list-item-title">{r.service_name}</span>
                                <span className="list-item-sub">{r.description.length > 90 ? r.description.slice(0, 90) + "…" : r.description}</span>
                                <span className="rec-meta">
                                    <span className={`category-badge cat-${r.category.toLowerCase().replace(" ", "-")}`}>{r.category}</span>
                                    <span className="rec-by">by {r.created_by_name}</span>
                                </span>
                            </div>
                            <div className="list-item-right">
                                <div className="vote-block-inline">
                                    <span className="vote-count">{r.vote_count}</span>
                                    <button
                                        className={`btn-vote-sm ${r.user_has_voted ? "voted" : ""}`}
                                        onClick={() => !r.user_has_voted && handleVote(r)}
                                        disabled={r.user_has_voted}
                                        title={r.user_has_voted ? "Already voted" : "Upvote"}
                                    >▲</button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

// ─── App Root ─────────────────────────────────────────────────────────────────

function App() {
    // Auth and Navigation State
    const [token, setToken] = React.useState(localStorage.getItem("token") || null);
    const [user, setUser] = React.useState(null);
    const [loading, setLoading] = React.useState(!!token);
    const [currentPage, setCurrentPage] = React.useState(token ? "dashboard" : "login");

    // Status connection state
    const [backendStatus, setBackendStatus] = React.useState({
        status: "connecting",
        message: "Attempting to contact backend...",
        version: "",
        database: ""
    });

    // Form inputs state - Login
    const [loginEmail, setLoginEmail] = React.useState("");
    const [loginPassword, setLoginPassword] = React.useState("");
    const [loginError, setLoginError] = React.useState("");
    const [loginSuccess, setLoginSuccess] = React.useState("");

    // Form inputs state - Signup
    const [signupName, setSignupName] = React.useState("");
    const [signupEmail, setSignupEmail] = React.useState("");
    const [signupFlat, setSignupFlat] = React.useState("");
    const [signupPassword, setSignupPassword] = React.useState("");
    const [signupConfirmPassword, setSignupConfirmPassword] = React.useState("");
    const [signupError, setSignupError] = React.useState("");

    // Check backend connection on boot
    React.useEffect(() => {
        fetch("/api/status")
            .then(res => { if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.json(); })
            .then(data => { setBackendStatus({ status: "connected", message: data.message, version: data.version, database: data.database_file || "SQLite" }); })
            .catch(err => { setBackendStatus({ status: "error", message: `Failed to connect to backend: ${err.message}`, version: "N/A", database: "N/A" }); });
    }, []);

    // Fetch user profile whenever token changes
    React.useEffect(() => {
        if (token) {
            setLoading(true);
            apiFetch("/api/auth/me", token)
                .then(profile => { setUser(profile); setLoading(false); })
                .catch(() => {
                    localStorage.removeItem("token");
                    setToken(null);
                    setUser(null);
                    setCurrentPage("login");
                    setLoading(false);
                });
        } else {
            setUser(null);
            setLoading(false);
        }
    }, [token]);

    const handleLogin = (e) => {
        e.preventDefault();
        setLoginError("");
        if (!loginEmail.trim() || !loginPassword) { setLoginError("Please enter both email and password."); return; }
        apiFetch("/api/auth/login", null, {
            method: "POST",
            body: JSON.stringify({ email: loginEmail, password: loginPassword })
        })
        .then(data => {
            localStorage.setItem("token", data.access_token);
            setToken(data.access_token);
            setLoginEmail(""); setLoginPassword("");
            setLoginSuccess(""); setCurrentPage("dashboard");
        })
        .catch(err => setLoginError(err.message));
    };

    const handleSignup = (e) => {
        e.preventDefault();
        setSignupError("");
        if (!signupName.trim() || !signupEmail.trim() || !signupFlat.trim() || !signupPassword || !signupConfirmPassword) {
            setSignupError("All fields are required."); return;
        }
        if (signupPassword !== signupConfirmPassword) { setSignupError("Passwords do not match."); return; }
        if (signupPassword.length < 6) { setSignupError("Password must be at least 6 characters."); return; }

        apiFetch("/api/auth/signup", null, {
            method: "POST",
            body: JSON.stringify({ name: signupName, email: signupEmail, flat_number: signupFlat, password: signupPassword, confirm_password: signupConfirmPassword })
        })
        .then(() => {
            setLoginSuccess("Account registered successfully! Please log in.");
            setSignupName(""); setSignupEmail(""); setSignupFlat(""); setSignupPassword(""); setSignupConfirmPassword("");
            setCurrentPage("login");
        })
        .catch(err => setSignupError(err.message));
    };

    const handleLogout = () => {
        localStorage.removeItem("token");
        setToken(null); setUser(null); setCurrentPage("login");
    };

    const renderContent = () => {
        if (loading) {
            return (<div className="card" style={{ textAlign: "center", padding: "3rem" }}><p>Loading...</p></div>);
        }

        if (!user) {
            if (currentPage === "signup") {
                return (
                    <div className="card">
                        <h2>Create CommUnity Account</h2>
                        <p className="welcome-text">Join your residential community intelligence portal.</p>
                        {signupError && <div className="error-panel">{signupError}</div>}
                        <form onSubmit={handleSignup}>
                            <div className="form-group"><label>Full Name</label>
                                <input type="text" value={signupName} onChange={e => setSignupName(e.target.value)} placeholder="Enter your full name" /></div>
                            <div className="form-group"><label>Email Address</label>
                                <input type="email" value={signupEmail} onChange={e => setSignupEmail(e.target.value)} placeholder="name@example.com" /></div>
                            <div className="form-group"><label>Flat / Unit Number</label>
                                <input type="text" value={signupFlat} onChange={e => setSignupFlat(e.target.value)} placeholder="e.g. Block A - 402" /></div>
                            <div className="form-group"><label>Password</label>
                                <input type="password" value={signupPassword} onChange={e => setSignupPassword(e.target.value)} placeholder="Minimum 6 characters" /></div>
                            <div className="form-group"><label>Confirm Password</label>
                                <input type="password" value={signupConfirmPassword} onChange={e => setSignupConfirmPassword(e.target.value)} placeholder="Re-enter password" /></div>
                            <button type="submit" className="btn-primary">Register Resident</button>
                        </form>
                        <div className="auth-switch">Already have an account?{" "}
                            <button className="btn-secondary" onClick={() => { setSignupError(""); setCurrentPage("login"); }}>Log In</button>
                        </div>
                    </div>
                );
            }
            return (
                <div className="card">
                    <h2>CommUnity Login</h2>
                    <p className="welcome-text">Log in to interact with your neighborhood portal.</p>
                    {loginSuccess && <div className="success-panel">{loginSuccess}</div>}
                    {loginError   && <div className="error-panel">{loginError}</div>}
                    <form onSubmit={handleLogin}>
                        <div className="form-group"><label>Email Address</label>
                            <input type="email" value={loginEmail} onChange={e => setLoginEmail(e.target.value)} placeholder="name@example.com" /></div>
                        <div className="form-group"><label>Password</label>
                            <input type="password" value={loginPassword} onChange={e => setLoginPassword(e.target.value)} placeholder="Enter password" /></div>
                        <button type="submit" className="btn-primary">Log In</button>
                    </form>
                    <div className="auth-switch">New resident?{" "}
                        <button className="btn-secondary" onClick={() => { setLoginError(""); setLoginSuccess(""); setCurrentPage("signup"); }}>Create an account</button>
                    </div>
                </div>
            );
        }

        switch (currentPage) {
            case "dashboard":
                return (
                    <div className="card">
                        <h2>Dashboard</h2>
                        <p className="welcome-text">Welcome back, <strong>{user.name}</strong>!</p>
                        <div className="status-container">
                            <h3>Backend Connectivity Status</h3>
                            <div className={`status-badge ${backendStatus.status}`}>{backendStatus.status.toUpperCase()}</div>
                            <div className="status-details">
                                <p><strong>Server Message:</strong> {backendStatus.message}</p>
                                <p><strong>API Version:</strong> {backendStatus.version}</p>
                                <p><strong>Connected Database:</strong> {backendStatus.database}</p>
                            </div>
                        </div>
                    </div>
                );
            case "contacts":
                return <ContactsPage token={token} />;
            case "recommendations":
                return <RecommendationsPage token={token} />;
            case "issues":
                return (
                    <div className="card">
                        <h2>Community Issues</h2>
                        <p className="info-text">Report and track maintenance, security, or utility issues in the community transparently.</p>
                        <div className="skeleton-item">Issue tracker — coming soon.</div>
                    </div>
                );
            case "profile":
                return (
                    <div className="card">
                        <h2>Resident Profile</h2>
                        <p className="info-text">View your account profile, unit configuration, and role status.</p>
                        <div className="profile-info">
                            <div className="profile-field"><strong>Resident Name</strong><span>{user.name}</span></div>
                            <div className="profile-field"><strong>Email Address</strong><span>{user.email}</span></div>
                            <div className="profile-field"><strong>Flat / Unit Number</strong><span>{user.flat_number}</span></div>
                            <div className="profile-field"><strong>Access Role</strong><span>{user.role}</span></div>
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
                        {[
                            ["dashboard",       "Dashboard"],
                            ["contacts",        "Contacts"],
                            ["recommendations", "Recommendations"],
                            ["issues",          "Issues"],
                            ["profile",         "Profile"]
                        ].map(([page, label]) => (
                            <button key={page}
                                className={`nav-link ${currentPage === page ? "active" : ""}`}
                                onClick={() => setCurrentPage(page)}
                            >{label}</button>
                        ))}
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

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
