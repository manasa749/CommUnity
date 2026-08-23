// ─── Constants ────────────────────────────────────────────────────────────────

const CONTACT_CATEGORIES = ["All", "Management", "Maintenance", "Security", "Emergency", "Other"];

const REC_CATEGORIES = [
    "All", "Broadband", "Plumber", "Electrician", "AC Service",
    "Appliance Repair", "Cleaning", "Tutor", "Healthcare", "Laundry", "Other"
];

const ISSUE_CATEGORIES = ["All", "Water", "Lift", "Parking", "Security", "Housekeeping", "Electrical", "Other"];
const ISSUE_STATUSES = ["All", "Open", "Assigned", "In Progress", "Resolved", "Closed"];

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
    const [sortBy, setSortBy] = React.useState("votes"); // "votes" | "newest"
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

    // Client-side sorting
    const sortedRecs = [...recs].sort((a, b) => {
        if (sortBy === "newest") {
            return new Date(b.created_date) - new Date(a.created_date) || b.vote_count - a.vote_count;
        } else {
            return b.vote_count - a.vote_count || new Date(b.created_date) - new Date(a.created_date);
        }
    });

    // List view
    return (
        <div className="card">
            <div className="section-header">
                <h2>Trusted Recommendations</h2>
                <button className="btn-primary btn-sm" onClick={() => setView("add")}>+ Add</button>
            </div>
            <p className="info-text">Browse service recommendations shared by your neighbours.</p>

            <div className="controls-row">
                <form onSubmit={handleSearch} className="search-bar-compact">
                    <input
                        type="text"
                        placeholder="Search recommendations..."
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                    />
                    <button type="submit" className="btn-primary btn-sm">Search</button>
                </form>
                <div className="filter-sort-controls">
                    <select
                        value={category}
                        onChange={e => handleCategoryChange(e.target.value)}
                        className="control-select"
                    >
                        {REC_CATEGORIES.map(cat => (
                            <option key={cat} value={cat}>{cat === "All" ? "All Categories" : cat}</option>
                        ))}
                    </select>
                    <select
                        value={sortBy}
                        onChange={e => setSortBy(e.target.value)}
                        className="control-select"
                    >
                        <option value="votes">Most Recommended</option>
                        <option value="newest">Newest</option>
                    </select>
                </div>
            </div>

            {loading && <p className="loading-text">Loading recommendations...</p>}
            {error   && <div className="error-panel">{error}</div>}

            {!loading && !error && recs.length === 0 && (
                <div className="empty-state">No recommendations found. Be the first to add one!</div>
            )}

            {!loading && recs.length > 0 && (
                <div className="list">
                    {sortedRecs.map(r => (
                        <div key={r.id} className="list-item compact-rec-card">
                            <div className="list-item-main" onClick={() => { setSelected(r); setView("detail"); setVoteMsg(""); }}>
                                <div className="rec-card-header">
                                    <span className="list-item-title">{r.service_name}</span>
                                    <span className={`category-badge cat-${r.category.toLowerCase().replace(" ", "-")}`}>{r.category}</span>
                                </div>
                                <span className="list-item-sub compact-desc">
                                    {r.description.length > 85 ? r.description.slice(0, 85) + "…" : r.description}
                                </span>
                                <div className="rec-card-footer">
                                    <span className="rec-by">by {r.created_by_name}</span>
                                </div>
                            </div>
                            <div className="list-item-right-compact">
                                <button
                                    className={`btn-vote-compact ${r.user_has_voted ? "voted" : ""}`}
                                    onClick={() => !r.user_has_voted && handleVote(r)}
                                    disabled={r.user_has_voted}
                                    title={r.user_has_voted ? "Already voted" : "Upvote"}
                                >
                                    ▲ {r.vote_count}
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

// ─── Report Issue Form ────────────────────────────────────────────────────────

function ReportIssueForm({ token, onAdded, onCancel }) {
    const [title, setTitle] = React.useState("");
    const [category, setCategory] = React.useState("Water");
    const [location, setLocation] = React.useState("");
    const [description, setDescription] = React.useState("");
    const [attachmentRef, setAttachmentRef] = React.useState("");
    const [error, setError] = React.useState("");
    const [saving, setSaving] = React.useState(false);

    const handleSubmit = (e) => {
        e.preventDefault();
        setError("");
        if (!title.trim() || !description.trim() || !location.trim()) {
            setError("Title, location, and description are required.");
            return;
        }
        setSaving(true);
        apiFetch("/api/issues", token, {
            method: "POST",
            body: JSON.stringify({
                title,
                category,
                location,
                description,
                attachment_ref: attachmentRef
            })
        })
        .then(issue => { setSaving(false); onAdded(issue); })
        .catch(err => { setError(err.message); setSaving(false); });
    };

    return (
        <div className="card">
            <button className="btn-back" onClick={onCancel}>← Back to Issues</button>
            <h2>Report a New Issue</h2>
            <p className="info-text">Submit maintenance, utility, or security concerns to the community management.</p>

            {error && <div className="error-panel">{error}</div>}

            <form onSubmit={handleSubmit}>
                <div className="form-group">
                    <label>Issue Title</label>
                    <input type="text" value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. Lift not working in Block B" />
                </div>
                <div className="form-group">
                    <label>Category</label>
                    <select value={category} onChange={e => setCategory(e.target.value)} className="form-select">
                        {ISSUE_CATEGORIES.filter(c => c !== "All").map(c => (
                            <option key={c} value={c}>{c}</option>
                        ))}
                    </select>
                </div>
                <div className="form-group">
                    <label>Location / Block</label>
                    <input type="text" value={location} onChange={e => setLocation(e.target.value)} placeholder="e.g. Block B, 3rd Floor" />
                </div>
                <div className="form-group">
                    <label>Description</label>
                    <textarea
                        value={description}
                        onChange={e => setDescription(e.target.value)}
                        placeholder="Provide details about the issue..."
                        rows="4"
                        className="form-textarea"
                    />
                </div>
                <div className="form-group">
                    <label>Optional Attachment Link</label>
                    <input type="text" value={attachmentRef} onChange={e => setAttachmentRef(e.target.value)} placeholder="e.g. Image URL or document link" />
                </div>
                <button type="submit" className="btn-primary" disabled={saving}>
                    {saving ? "Submitting..." : "Report Issue"}
                </button>
            </form>
        </div>
    );
}

// ─── Issues Page ──────────────────────────────────────────────────────────────

function IssuesPage({ token, userRole }) {
    const [view, setView] = React.useState("list"); // "list" | "add" | "detail"
    const [issues, setIssues] = React.useState([]);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState("");
    const [search, setSearch] = React.useState("");
    const [category, setCategory] = React.useState("All");
    const [statusFilter, setStatusFilter] = React.useState("All");
    const [onlyMine, setOnlyMine] = React.useState(false);
    const [selected, setSelected] = React.useState(null);
    const [adminUpdateError, setAdminUpdateError] = React.useState("");
    
    // Admin update state fields
    const [adminStatus, setAdminStatus] = React.useState("Open");
    const [adminAssignee, setAdminAssignee] = React.useState("");
    const [updating, setUpdating] = React.useState(false);

    const fetchIssues = (cat, stat, q, mine) => {
        setLoading(true);
        setError("");
        const params = new URLSearchParams();
        if (cat && cat !== "All") params.append("category", cat);
        if (stat && stat !== "All") params.append("status", stat);
        if (q && q.trim()) params.append("search", q.trim());
        if (mine) params.append("only_mine", "true");
        
        apiFetch(`/api/issues?${params.toString()}`, token)
            .then(data => { setIssues(data); setLoading(false); })
            .catch(err => { setError(err.message); setLoading(false); });
    };

    React.useEffect(() => {
        fetchIssues("All", "All", "", false);
    }, []);

    const handleSearch = (e) => {
        e.preventDefault();
        fetchIssues(category, statusFilter, search, onlyMine);
    };

    const handleCategoryChange = (e) => {
        const cat = e.target.value;
        setCategory(cat);
        fetchIssues(cat, statusFilter, search, onlyMine);
    };

    const handleStatusFilterChange = (e) => {
        const stat = e.target.value;
        setStatusFilter(stat);
        fetchIssues(category, stat, search, onlyMine);
    };

    const handleOnlyMineChange = (e) => {
        const mine = e.target.checked;
        setOnlyMine(mine);
        fetchIssues(category, statusFilter, search, mine);
    };

    const handleOpenDetail = (issue) => {
        setSelected(issue);
        setAdminStatus(issue.status);
        setAdminAssignee(issue.assigned_to || "");
        setAdminUpdateError("");
        setView("detail");
    };

    const handleAdminUpdate = (e) => {
        e.preventDefault();
        setAdminUpdateError("");
        setUpdating(true);
        apiFetch(`/api/issues/${selected.id}`, token, {
            method: "PUT",
            body: JSON.stringify({
                status: adminStatus,
                assigned_to: adminAssignee
            })
        })
        .then(updatedIssue => {
            setUpdating(false);
            setSelected(updatedIssue);
            setIssues(prev => prev.map(i => i.id === updatedIssue.id ? updatedIssue : i));
        })
        .catch(err => {
            setAdminUpdateError(err.message);
            setUpdating(false);
        });
    };

    if (view === "add") {
        return <ReportIssueForm token={token} onAdded={() => { setView("list"); fetchIssues(category, statusFilter, search, onlyMine); }} onCancel={() => setView("list")} />;
    }

    if (view === "detail" && selected) {
        return (
            <div className="card">
                <button className="btn-back" onClick={() => { setView("list"); setSelected(null); }}>← Back to Issues</button>
                <div className="rec-detail-header">
                    <div>
                        <h2>{selected.title}</h2>
                        <div className="badge-row" style={{ display: 'flex', gap: '0.5rem', marginTop: '0.375rem' }}>
                            <span className={`category-badge cat-${selected.category.toLowerCase()}`}>{selected.category}</span>
                            <span className={`status-badge status-${selected.status.toLowerCase().replace(" ", "-")}`}>{selected.status}</span>
                        </div>
                    </div>
                </div>

                <div className="detail-grid">
                    <div className="detail-row detail-description">
                        <strong>Description</strong>
                        <span>{selected.description}</span>
                    </div>
                    <div className="detail-row"><strong>Location / Block</strong><span>{selected.location}</span></div>
                    <div className="detail-row"><strong>Reported By</strong><span>{selected.created_by_name}</span></div>
                    <div className="detail-row"><strong>Reported Date</strong><span>{selected.created_date}</span></div>
                    <div className="detail-row"><strong>Last Updated</strong><span>{selected.updated_date}</span></div>
                    <div className="detail-row"><strong>Assigned To</strong><span>{selected.assigned_to || "Unassigned"}</span></div>
                    {selected.attachment_ref && (
                        <div className="detail-row">
                            <strong>Attachment Reference</strong>
                            <span>
                                <a href={selected.attachment_ref} target="_blank" rel="noopener noreferrer" className="attachment-link">
                                    View Attachment
                                </a>
                            </span>
                        </div>
                    )}
                </div>

                {userRole === "Admin" && (
                    <div className="admin-controls-panel" style={{ marginTop: '1.5rem', paddingTop: '1.25rem', borderTop: '1px solid var(--border-color)' }}>
                        <h3>Admin Status & Assignment Controls</h3>
                        {adminUpdateError && <div className="error-panel">{adminUpdateError}</div>}
                        <form onSubmit={handleAdminUpdate} style={{ marginTop: '0.75rem' }}>
                            <div className="form-group">
                                <label>Status</label>
                                <select value={adminStatus} onChange={e => setAdminStatus(e.target.value)} className="form-select">
                                    {ISSUE_STATUSES.filter(s => s !== "All").map(s => (
                                        <option key={s} value={s}>{s}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="form-group">
                                <label>Assigned To</label>
                                <input
                                    type="text"
                                    value={adminAssignee}
                                    onChange={e => setAdminAssignee(e.target.value)}
                                    placeholder="Assign to staff / department"
                                />
                            </div>
                            <button type="submit" className="btn-primary" disabled={updating}>
                                {updating ? "Saving Changes..." : "Update Issue Status / Assignment"}
                            </button>
                        </form>
                    </div>
                )}
            </div>
        );
    }

    return (
        <div className="card">
            <div className="section-header">
                <h2>Community Issues</h2>
                <button className="btn-primary btn-sm" onClick={() => setView("add")}>+ Report Issue</button>
            </div>
            <p className="info-text">Report and track maintenance, security, or utility issues in the community.</p>

            <div className="controls-row">
                <form onSubmit={handleSearch} className="search-bar-compact">
                    <input
                        type="text"
                        placeholder="Search issues..."
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                    />
                    <button type="submit" className="btn-primary btn-sm">Search</button>
                </form>
                <div className="filter-sort-controls">
                    <select value={category} onChange={handleCategoryChange} className="control-select">
                        {ISSUE_CATEGORIES.map(cat => (
                            <option key={cat} value={cat}>{cat === "All" ? "All Categories" : cat}</option>
                        ))}
                    </select>
                    <select value={statusFilter} onChange={handleStatusFilterChange} className="control-select">
                        {ISSUE_STATUSES.map(stat => (
                            <option key={stat} value={stat}>{stat === "All" ? "All Statuses" : stat}</option>
                        ))}
                    </select>
                </div>
            </div>

            {userRole !== "Admin" && (
                <div className="form-group-checkbox" style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                        type="checkbox"
                        id="onlyMineCheck"
                        checked={onlyMine}
                        onChange={handleOnlyMineChange}
                        style={{ width: 'auto', cursor: 'pointer' }}
                    />
                    <label htmlFor="onlyMineCheck" style={{ fontSize: '0.85rem', color: 'var(--text-muted)', cursor: 'pointer', userSelect: 'none' }}>
                        Show only issues reported by me
                    </label>
                </div>
            )}

            {loading && <p className="loading-text">Loading issues...</p>}
            {error   && <div className="error-panel">{error}</div>}

            {!loading && !error && issues.length === 0 && (
                <div className="empty-state">No issues found. Everything is running smoothly!</div>
            )}

            {!loading && issues.length > 0 && (
                <div className="list">
                    {issues.map(i => (
                        <div key={i.id} className="list-item compact-rec-card" onClick={() => handleOpenDetail(i)}>
                            <div className="list-item-main">
                                <div className="rec-card-header">
                                    <span className="list-item-title">{i.title}</span>
                                    <span className={`category-badge cat-${i.category.toLowerCase()}`}>{i.category}</span>
                                    <span className={`status-badge status-${i.status.toLowerCase().replace(" ", "-")}`} style={{ fontSize: '0.7rem', padding: '0.1rem 0.4rem', borderRadius: '4px', textTransform: 'uppercase', fontWeight: 'bold' }}>{i.status}</span>
                                </div>
                                <span className="list-item-sub compact-desc">
                                    {i.description.length > 85 ? i.description.slice(0, 85) + "…" : i.description}
                                </span>
                                <div className="rec-card-footer" style={{ display: 'flex', gap: '0.75rem', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                                    <span>📍 {i.location}</span>
                                    <span>by {i.created_by_name}</span>
                                    <span>{i.created_date}</span>
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
    const [menuOpen, setMenuOpen] = React.useState(false);

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
                return <IssuesPage token={token} userRole={user.role} />;
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
        <div className="app-container" onClick={() => setMenuOpen(false)}>
            <header className="header" onClick={e => e.stopPropagation()}>
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
                            ["issues",          "Issues"]
                        ].map(([page, label]) => (
                            <button key={page}
                                className={`nav-link ${currentPage === page ? "active" : ""}`}
                                onClick={() => setCurrentPage(page)}
                            >{label}</button>
                        ))}
                    </nav>
                )}
                {user && (
                    <div className="user-menu-container">
                        <button className="user-menu-trigger" onClick={() => setMenuOpen(!menuOpen)}>
                            👤 {user.name} ({user.flat_number}) <span className="arrow">▼</span>
                        </button>
                        {menuOpen && (
                            <div className="user-dropdown">
                                <button className="dropdown-item" onClick={() => { setCurrentPage("profile"); setMenuOpen(false); }}>
                                    Profile
                                </button>
                                <button className="dropdown-item" onClick={() => { handleLogout(); setMenuOpen(false); }}>
                                    Logout
                                </button>
                            </div>
                        )}
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
