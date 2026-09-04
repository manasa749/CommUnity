// ─── Constants ────────────────────────────────────────────────────────────────

const CONTACT_CATEGORIES = ["All", "Management", "Maintenance", "Security", "Emergency", "Other"];

const REC_CATEGORIES = [
    "All", "Broadband", "Plumber", "Electrician", "AC Service",
    "Appliance Repair", "Cleaning", "Tutor", "Healthcare", "Laundry", "Other"
];

const ISSUE_CATEGORIES = ["All", "Water", "Lift", "Parking", "Security", "Housekeeping", "Electrical", "Other"];
const ISSUE_STATUSES = ["All", "Open", "Assigned", "In Progress", "Resolved", "Closed"];
const ISSUE_ASSIGNEES = [
    "Maintenance Manager", "Plumbing & Electrical Lead",
    "Housekeeping Supervisor", "Head of Security", "Other"
];

const ANNOUNCEMENT_CATEGORIES = ["General", "Maintenance", "Security", "Water", "Other"];

// ─── API helper ───────────────────────────────────────────────────────────────

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
        setLoading(true); setError("");
        const params = new URLSearchParams();
        if (cat && cat !== "All") params.append("category", cat);
        if (q && q.trim()) params.append("search", q.trim());
        apiFetch(`/api/contacts?${params.toString()}`, token)
            .then(data => { setContacts(data); setLoading(false); })
            .catch(err => { setError(err.message); setLoading(false); });
    };

    React.useEffect(() => { fetchContacts("All", ""); }, []);

    const handleSearch = (e) => { e.preventDefault(); fetchContacts(category, search); };
    const handleCategoryChange = (cat) => { setCategory(cat); fetchContacts(cat, search); };

    if (selected) {
        return (
            <div className="card">
                <button className="btn-back" onClick={() => setSelected(null)}>Back to Contacts</button>
                <h2>{selected.name}</h2>
                <span className={`category-badge cat-${selected.category.toLowerCase()}`}>{selected.category}</span>
                <div className="detail-grid">
                    <div className="detail-row"><strong>Designation</strong><span>{selected.designation}</span></div>
                    {selected.phone && <div className="detail-row"><strong>Phone</strong><span>{selected.phone}</span></div>}
                    {selected.email && <div className="detail-row"><strong>Email</strong><span>{selected.email}</span></div>}
                    {selected.availability && <div className="detail-row"><strong>Availability</strong><span>{selected.availability}</span></div>}
                </div>
            </div>
        );
    }

    return (
        <div className="card">
            <h2>Community Contacts</h2>
            <p className="info-text">Find emergency numbers, management, maintenance, and security contacts.</p>
            <form onSubmit={handleSearch} className="search-bar">
                <input type="text" placeholder="Search contacts..." value={search} onChange={e => setSearch(e.target.value)} />
                <button type="submit" className="btn-primary btn-sm">Search</button>
            </form>
            <div className="filter-tabs">
                {CONTACT_CATEGORIES.map(cat => (
                    <button key={cat} className={`filter-tab ${category === cat ? "active" : ""}`} onClick={() => handleCategoryChange(cat)}>{cat}</button>
                ))}
            </div>
            {loading && <p className="loading-text">Loading contacts...</p>}
            {error && <div className="error-panel">{error}</div>}
            {!loading && !error && contacts.length === 0 && <div className="empty-state">No contacts found.</div>}
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
    const [categoryOther, setCategoryOther] = React.useState("");
    const [description, setDescription] = React.useState("");
    const [contactInfo, setContactInfo] = React.useState("");
    const [error, setError] = React.useState("");
    const [saving, setSaving] = React.useState(false);

    const effectiveCategory = category === "Other" ? categoryOther.trim() : category;

    const handleSubmit = (e) => {
        e.preventDefault(); setError("");
        if (!serviceName.trim() || !description.trim()) { setError("Service name and description are required."); return; }
        if (category === "Other" && !categoryOther.trim()) { setError("Please enter a category name."); return; }
        setSaving(true);
        apiFetch("/api/recommendations", token, {
            method: "POST",
            body: JSON.stringify({ service_name: serviceName, category: effectiveCategory, description, contact_info: contactInfo })
        })
            .then(rec => { setSaving(false); onAdded(rec); })
            .catch(err => { setError(err.message); setSaving(false); });
    };

    return (
        <div className="card">
            <button className="btn-back" onClick={onCancel}>Back to Recommendations</button>
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
                    <select value={category} onChange={e => { setCategory(e.target.value); setCategoryOther(""); }} className="form-select">
                        {REC_CATEGORIES.filter(c => c !== "All").map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                    {category === "Other" && (
                        <input type="text" value={categoryOther} onChange={e => setCategoryOther(e.target.value)} placeholder="Enter category name" style={{ marginTop: "0.5rem" }} />
                    )}
                </div>
                <div className="form-group">
                    <label>Description</label>
                    <textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="Describe the service and why you recommend it..." rows="4" className="form-textarea" />
                </div>
                <div className="form-group">
                    <label>Contact Information <span className="label-optional">(optional)</span></label>
                    <input type="text" value={contactInfo} onChange={e => setContactInfo(e.target.value)} placeholder="e.g. phone number or address" />
                </div>
                <button type="submit" className="btn-primary" disabled={saving}>{saving ? "Saving..." : "Submit Recommendation"}</button>
            </form>
        </div>
    );
}

// ─── Edit Recommendation Form ─────────────────────────────────────────────────

function EditRecommendationForm({ token, rec, onSaved, onCancel }) {
    // If existing category isn't in the predefined list, treat it as a custom "Other" value
    const knownCats = REC_CATEGORIES.filter(c => c !== "All");
    const initCat = knownCats.includes(rec.category) ? rec.category : "Other";
    const initOther = knownCats.includes(rec.category) ? "" : rec.category;

    const [serviceName, setServiceName] = React.useState(rec.service_name);
    const [category, setCategory] = React.useState(initCat);
    const [categoryOther, setCategoryOther] = React.useState(initOther);
    const [description, setDescription] = React.useState(rec.description);
    const [contactInfo, setContactInfo] = React.useState(rec.contact_info || "");
    const [error, setError] = React.useState("");
    const [saving, setSaving] = React.useState(false);

    const effectiveCategory = category === "Other" ? categoryOther.trim() : category;

    const handleSubmit = (e) => {
        e.preventDefault(); setError("");
        if (!serviceName.trim() || !description.trim()) { setError("Service name and description are required."); return; }
        if (category === "Other" && !categoryOther.trim()) { setError("Please enter a category name."); return; }
        setSaving(true);
        apiFetch(`/api/recommendations/${rec.id}`, token, {
            method: "PUT",
            body: JSON.stringify({ service_name: serviceName, category: effectiveCategory, description, contact_info: contactInfo })
        })
            .then(updated => { setSaving(false); onSaved(updated); })
            .catch(err => { setError(err.message); setSaving(false); });
    };

    return (
        <div className="card">
            <button className="btn-back" onClick={onCancel}>Cancel Edit</button>
            <h2>Edit Recommendation</h2>
            {error && <div className="error-panel">{error}</div>}
            <form onSubmit={handleSubmit}>
                <div className="form-group">
                    <label>Service / Provider Name</label>
                    <input type="text" value={serviceName} onChange={e => setServiceName(e.target.value)} />
                </div>
                <div className="form-group">
                    <label>Category</label>
                    <select value={category} onChange={e => { setCategory(e.target.value); setCategoryOther(""); }} className="form-select">
                        {REC_CATEGORIES.filter(c => c !== "All").map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                    {category === "Other" && (
                        <input type="text" value={categoryOther} onChange={e => setCategoryOther(e.target.value)} placeholder="Enter category name" style={{ marginTop: "0.5rem" }} />
                    )}
                </div>
                <div className="form-group">
                    <label>Description</label>
                    <textarea value={description} onChange={e => setDescription(e.target.value)} rows="4" className="form-textarea" />
                </div>
                <div className="form-group">
                    <label>Contact Information <span className="label-optional">(optional)</span></label>
                    <input type="text" value={contactInfo} onChange={e => setContactInfo(e.target.value)} />
                </div>
                <button type="submit" className="btn-primary" disabled={saving}>{saving ? "Saving..." : "Save Changes"}</button>
            </form>
        </div>
    );
}

// ─── Recommendations Page ─────────────────────────────────────────────────────

function RecommendationsPage({ token, user }) {
    const [view, setView] = React.useState("list");
    const [recs, setRecs] = React.useState([]);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState("");
    const [search, setSearch] = React.useState("");
    const [category, setCategory] = React.useState("All");
    const [sortBy, setSortBy] = React.useState("votes");
    const [selected, setSelected] = React.useState(null);
    const [voteMsg, setVoteMsg] = React.useState("");
    const [actionMsg, setActionMsg] = React.useState("");

    const fetchRecs = (cat, q) => {
        setLoading(true); setError("");
        const params = new URLSearchParams();
        if (cat && cat !== "All") params.append("category", cat);
        if (q && q.trim()) params.append("search", q.trim());
        apiFetch(`/api/recommendations?${params.toString()}`, token)
            .then(data => { setRecs(data); setLoading(false); })
            .catch(err => { setError(err.message); setLoading(false); });
    };

    React.useEffect(() => { fetchRecs("All", ""); }, []);

    const handleSearch = (e) => { e.preventDefault(); fetchRecs(category, search); };
    const handleCategoryChange = (cat) => { setCategory(cat); fetchRecs(cat, search); };

    const handleVote = (rec) => {
        setVoteMsg("");
        apiFetch(`/api/recommendations/${rec.id}/vote`, token, { method: "POST" })
            .then(updated => {
                setRecs(prev => prev.map(r => r.id === updated.id ? updated : r));
                if (selected && selected.id === updated.id) setSelected(updated);
            })
            .catch(err => { setVoteMsg(err.message || "Could not update vote."); });
    };

    const handleDelete = (rec) => {
        if (!window.confirm(`Remove "${rec.service_name}" from recommendations?`)) return;
        apiFetch(`/api/recommendations/${rec.id}`, token, { method: "DELETE" })
            .then(() => {
                setRecs(prev => prev.filter(r => r.id !== rec.id));
                if (selected && selected.id === rec.id) { setSelected(null); setView("list"); }
            })
            .catch(err => { setActionMsg(err.message); });
    };

    // After edit: go back to list, refresh. After add: go to list too.
    const handleAdded = () => { setView("list"); fetchRecs(category, search); };
    const handleSaved = () => { setView("list"); fetchRecs(category, search); };

    const canModify = (rec) => user && (rec.created_by_user_id === user.id || user.role === "Admin");

    if (view === "add") return <AddRecommendationForm token={token} onAdded={handleAdded} onCancel={() => setView("list")} />;
    if (view === "edit" && selected) return <EditRecommendationForm token={token} rec={selected} onSaved={handleSaved} onCancel={() => setView("detail")} />;

    if (view === "detail" && selected) {
        return (
            <div className="card">
                <button className="btn-back" onClick={() => { setView("list"); setSelected(null); setVoteMsg(""); setActionMsg(""); }}>Back to Recommendations</button>
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
                            onClick={() => handleVote(selected)}
                            title={selected.user_has_voted ? "Click to remove your vote" : "Click to upvote"}
                        >
                            {selected.user_has_voted ? "Voted" : "Upvote"}
                        </button>
                    </div>
                </div>
                {voteMsg && <div className="error-panel">{voteMsg}</div>}
                {actionMsg && <div className="error-panel">{actionMsg}</div>}
                <div className="detail-grid">
                    <div className="detail-row detail-description">
                        <strong>About</strong>
                        <span>{selected.description}</span>
                    </div>
                    {selected.contact_info && (
                        <div className="detail-row"><strong>Contact</strong><span>{selected.contact_info}</span></div>
                    )}
                    <div className="detail-row"><strong>Date added</strong><span>{selected.created_date}</span></div>
                </div>
                {canModify(selected) && (
                    <div className="detail-actions">
                        <button className="btn-primary btn-sm" style={{ width: "auto" }} onClick={() => { setActionMsg(""); setView("edit"); }}>Edit</button>
                        <button className="btn-danger-outline btn-sm" onClick={() => handleDelete(selected)}>Delete</button>
                    </div>
                )}
            </div>
        );
    }

    const sortedRecs = [...recs].sort((a, b) =>
        sortBy === "newest"
            ? new Date(b.created_date) - new Date(a.created_date) || b.vote_count - a.vote_count
            : b.vote_count - a.vote_count || new Date(b.created_date) - new Date(a.created_date)
    );

    return (
        <div className="card">
            <div className="section-header">
                <h2>Trusted Recommendations</h2>
                <button className="btn-primary btn-sm" onClick={() => setView("add")}>+ Add</button>
            </div>
            <p className="info-text">Browse service recommendations shared by your neighbours.</p>
            <div className="controls-row">
                <form onSubmit={handleSearch} className="search-bar-compact">
                    <input type="text" placeholder="Search recommendations..." value={search} onChange={e => setSearch(e.target.value)} />
                    <button type="submit" className="btn-primary btn-sm">Search</button>
                </form>
                <div className="filter-sort-controls">
                    <select value={category} onChange={e => handleCategoryChange(e.target.value)} className="control-select">
                        {REC_CATEGORIES.map(cat => <option key={cat} value={cat}>{cat === "All" ? "All Categories" : cat}</option>)}
                    </select>
                    <select value={sortBy} onChange={e => setSortBy(e.target.value)} className="control-select">
                        <option value="votes">Most Recommended</option>
                        <option value="newest">Newest</option>
                    </select>
                </div>
            </div>
            {loading && <p className="loading-text">Loading recommendations...</p>}
            {error && <div className="error-panel">{error}</div>}
            {!loading && !error && recs.length === 0 && <div className="empty-state">No recommendations found. Be the first to add one!</div>}
            {!loading && recs.length > 0 && (
                <div className="list">
                    {sortedRecs.map(r => (
                        <div key={r.id} className="list-item compact-rec-card">
                            <div className="list-item-main" onClick={() => { setSelected(r); setView("detail"); setVoteMsg(""); setActionMsg(""); }}>
                                <div className="rec-card-header">
                                    <span className="list-item-title">{r.service_name}</span>
                                    <span className={`category-badge cat-${r.category.toLowerCase().replace(" ", "-")}`}>{r.category}</span>
                                </div>
                                <span className="list-item-sub compact-desc">
                                    {r.description.length > 85 ? r.description.slice(0, 85) + "..." : r.description}
                                </span>
                            </div>
                            <div className="list-item-right-compact">
                                <button
                                    className={`btn-vote-compact ${r.user_has_voted ? "voted" : ""}`}
                                    onClick={() => handleVote(r)}
                                    title={r.user_has_voted ? "Click to remove your vote" : "Upvote"}
                                >
                                    {r.vote_count}
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
    const [categoryOther, setCategoryOther] = React.useState("");
    const [location, setLocation] = React.useState("");
    const [description, setDescription] = React.useState("");
    const [attachmentRef, setAttachmentRef] = React.useState("");
    const [error, setError] = React.useState("");
    const [saving, setSaving] = React.useState(false);

    const effectiveCategory = category === "Other" ? categoryOther.trim() : category;

    const handleSubmit = (e) => {
        e.preventDefault(); setError("");
        if (!title.trim() || !description.trim() || !location.trim()) {
            setError("Title, location, and description are required."); return;
        }
        if (category === "Other" && !categoryOther.trim()) { setError("Please enter a category name."); return; }
        setSaving(true);
        apiFetch("/api/issues", token, {
            method: "POST",
            body: JSON.stringify({ title, category: effectiveCategory, location, description, attachment_ref: attachmentRef })
        })
            .then(issue => { setSaving(false); onAdded(issue); })
            .catch(err => { setError(err.message); setSaving(false); });
    };

    return (
        <div className="card">
            <button className="btn-back" onClick={onCancel}>Back to Issues</button>
            <h2>Report a New Issue</h2>
            <p className="info-text">Submit maintenance, utility, or security concerns to community management.</p>
            {error && <div className="error-panel">{error}</div>}
            <form onSubmit={handleSubmit}>
                <div className="form-group">
                    <label>Issue Title</label>
                    <input type="text" value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. Lift not working in Block B" />
                </div>
                <div className="form-group">
                    <label>Category</label>
                    <select value={category} onChange={e => { setCategory(e.target.value); setCategoryOther(""); }} className="form-select">
                        {ISSUE_CATEGORIES.filter(c => c !== "All").map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                    {category === "Other" && (
                        <input type="text" value={categoryOther} onChange={e => setCategoryOther(e.target.value)} placeholder="Enter category name" style={{ marginTop: "0.5rem" }} />
                    )}
                </div>
                <div className="form-group">
                    <label>Location / Block</label>
                    <input type="text" value={location} onChange={e => setLocation(e.target.value)} placeholder="e.g. Block B, 3rd Floor" />
                </div>
                <div className="form-group">
                    <label>Description</label>
                    <textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="Provide details about the issue..." rows="4" className="form-textarea" />
                </div>
                <div className="form-group">
                    <label>Attachment Link <span className="label-optional">(optional)</span></label>
                    <input type="text" value={attachmentRef} onChange={e => setAttachmentRef(e.target.value)} placeholder="e.g. Image URL or document link" />
                </div>
                <button type="submit" className="btn-primary" disabled={saving}>{saving ? "Submitting..." : "Report Issue"}</button>
            </form>
        </div>
    );
}

// ─── Issues Page ──────────────────────────────────────────────────────────────

function IssuesPage({ token, user }) {
    const userRole = user ? user.role : "Resident";
    const userId = user ? user.id : null;

    const [view, setView] = React.useState("list");
    const [issues, setIssues] = React.useState([]);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState("");
    const [search, setSearch] = React.useState("");
    const [category, setCategory] = React.useState("All");
    const [statusFilter, setStatusFilter] = React.useState("All");
    const [onlyMine, setOnlyMine] = React.useState(false);
    const [selected, setSelected] = React.useState(null);
    const [adminUpdateError, setAdminUpdateError] = React.useState("");
    const [adminStatus, setAdminStatus] = React.useState("Open");
    const [adminAssignee, setAdminAssignee] = React.useState("");
    const [adminAssigneeOther, setAdminAssigneeOther] = React.useState("");
    const [adminNote, setAdminNote] = React.useState("");
    const [updating, setUpdating] = React.useState(false);

    const fetchIssues = (cat, stat, q, mine) => {
        setLoading(true); setError("");
        const params = new URLSearchParams();
        if (cat && cat !== "All") params.append("category", cat);
        if (stat && stat !== "All") params.append("status", stat);
        if (q && q.trim()) params.append("search", q.trim());
        if (mine) params.append("only_mine", "true");
        apiFetch(`/api/issues?${params.toString()}`, token)
            .then(data => { setIssues(data); setLoading(false); })
            .catch(err => { setError(err.message); setLoading(false); });
    };

    React.useEffect(() => { fetchIssues("All", "All", "", userRole === "Admin"); }, []);

    const handleSearch = (e) => { e.preventDefault(); fetchIssues(category, statusFilter, search, onlyMine); };
    const handleCategoryChange = (e) => { const cat = e.target.value; setCategory(cat); fetchIssues(cat, statusFilter, search, onlyMine); };
    const handleStatusFilterChange = (e) => { const stat = e.target.value; setStatusFilter(stat); fetchIssues(category, stat, search, onlyMine); };
    const handleOnlyMineChange = (e) => { const mine = e.target.checked; setOnlyMine(mine); fetchIssues(category, statusFilter, search, mine); };

    const handleOpenDetail = (issue) => {
        setSelected(issue);
        setAdminStatus(issue.status);
        // Detect if stored assignee is a custom (non-predefined) value
        const stored = issue.assigned_to || "";
        const isPredefined = stored === "" || ISSUE_ASSIGNEES.includes(stored);
        setAdminAssignee(isPredefined ? stored : "Other");
        setAdminAssigneeOther(isPredefined ? "" : stored);
        setAdminNote(issue.admin_note || "");
        setAdminUpdateError("");
        setView("detail");
    };

    const handleAdminUpdate = (e) => {
        e.preventDefault(); setAdminUpdateError(""); setUpdating(true);
        if (adminAssignee === "Other" && !adminAssigneeOther.trim()) {
            setAdminUpdateError("Please enter a custom assignee name."); setUpdating(false); return;
        }
        const effectiveAssignee = adminAssignee === "Other" ? adminAssigneeOther.trim() : adminAssignee;
        apiFetch(`/api/issues/${selected.id}`, token, {
            method: "PUT",
            body: JSON.stringify({ status: adminStatus, assigned_to: effectiveAssignee, admin_note: adminNote })
        })
            .then(() => {
                setUpdating(false);
                // Refresh list and return to it
                fetchIssues(category, statusFilter, search, onlyMine);
                setView("list"); setSelected(null);
            })
            .catch(err => { setAdminUpdateError(err.message); setUpdating(false); });
    };

    if (view === "add") {
        return <ReportIssueForm token={token}
            onAdded={() => { setView("list"); fetchIssues(category, statusFilter, search, onlyMine); }}
            onCancel={() => setView("list")} />;
    }

    if (view === "detail" && selected) {
        const isCreator = selected.created_by_user_id === userId;
        const reporterLabel = userRole === "Admin" ? selected.created_by_name : (isCreator ? "You" : null);

        return (
            <div className="card">
                <button className="btn-back" onClick={() => { setView("list"); setSelected(null); }}>Back to Issues</button>
                <div className="rec-detail-header">
                    <div>
                        <h2>{selected.title}</h2>
                        <div className="badge-row" style={{ display: "flex", gap: "0.5rem", marginTop: "0.375rem" }}>
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
                    {reporterLabel && (
                        <div className="detail-row"><strong>Reported By</strong><span>{reporterLabel}</span></div>
                    )}
                    <div className="detail-row"><strong>Reported Date</strong><span>{selected.created_date}</span></div>
                    <div className="detail-row"><strong>Last Updated</strong><span>{selected.updated_date}</span></div>
                    <div className="detail-row"><strong>Assigned To</strong><span>{selected.assigned_to || "Unassigned"}</span></div>
                    {selected.admin_note && (
                        <div className="detail-row detail-description">
                            <strong>Resolution Note</strong>
                            <span>{selected.admin_note}</span>
                        </div>
                    )}
                    {selected.attachment_ref && (
                        <div className="detail-row">
                            <strong>Attachment</strong>
                            <span><a href={selected.attachment_ref} target="_blank" rel="noopener noreferrer" className="attachment-link">View Attachment</a></span>
                        </div>
                    )}
                </div>

                {userRole === "Admin" && (
                    <div className="admin-controls-panel" style={{ marginTop: "1.5rem", paddingTop: "1.25rem", borderTop: "1px solid var(--border-color)" }}>
                        <h3>Admin Controls</h3>
                        {adminUpdateError && <div className="error-panel">{adminUpdateError}</div>}
                        <form onSubmit={handleAdminUpdate} style={{ marginTop: "0.75rem" }}>
                            <div className="form-group">
                                <label>Status</label>
                                <select value={adminStatus} onChange={e => setAdminStatus(e.target.value)} className="form-select">
                                    {ISSUE_STATUSES.filter(s => s !== "All").map(s => <option key={s} value={s}>{s}</option>)}
                                </select>
                            </div>
                            <div className="form-group">
                                <label>Assigned To</label>
                                <select value={adminAssignee} onChange={e => { setAdminAssignee(e.target.value); setAdminAssigneeOther(""); }} className="form-select">
                                    <option value="">Unassigned</option>
                                    {ISSUE_ASSIGNEES.map(a => <option key={a} value={a}>{a}</option>)}
                                </select>
                                {adminAssignee === "Other" && (
                                    <input type="text" value={adminAssigneeOther} onChange={e => setAdminAssigneeOther(e.target.value)} placeholder="Enter assignee name or role" style={{ marginTop: "0.5rem" }} />
                                )}
                            </div>
                            <div className="form-group">
                                <label>Admin / Resolution Note <span className="label-optional">(optional)</span></label>
                                <textarea value={adminNote} onChange={e => setAdminNote(e.target.value)} rows="3" className="form-textarea" placeholder="Add a resolution note or update for the community..." />
                            </div>
                            <button type="submit" className="btn-primary" disabled={updating}>{updating ? "Saving..." : "Save Changes"}</button>
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
                    <input type="text" placeholder="Search issues..." value={search} onChange={e => setSearch(e.target.value)} />
                    <button type="submit" className="btn-primary btn-sm">Search</button>
                </form>
                <div className="filter-sort-controls">
                    <select value={category} onChange={handleCategoryChange} className="control-select">
                        {ISSUE_CATEGORIES.map(cat => <option key={cat} value={cat}>{cat === "All" ? "All Categories" : cat}</option>)}
                    </select>
                    <select value={statusFilter} onChange={handleStatusFilterChange} className="control-select">
                        {ISSUE_STATUSES.map(stat => <option key={stat} value={stat}>{stat === "All" ? "All Statuses" : stat}</option>)}
                    </select>
                </div>
            </div>

            {userRole !== "Admin" && (
                <div style={{ marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <input type="checkbox" id="onlyMineCheck" checked={onlyMine} onChange={handleOnlyMineChange} style={{ width: "auto", cursor: "pointer" }} />
                    <label htmlFor="onlyMineCheck" style={{ fontSize: "0.85rem", color: "var(--text-muted)", cursor: "pointer", userSelect: "none" }}>
                        Show only issues reported by me
                    </label>
                </div>
            )}

            {loading && <p className="loading-text">Loading issues...</p>}
            {error && <div className="error-panel">{error}</div>}
            {!loading && !error && issues.length === 0 && <div className="empty-state">No issues found. Everything is running smoothly!</div>}

            {!loading && issues.length > 0 && (
                <div className="list">
                    {issues.map(i => (
                        <div key={i.id} className="list-item issue-list-item" onClick={() => handleOpenDetail(i)}>
                            <div className="list-item-main">
                                <div className="rec-card-header">
                                    <span className="list-item-title">{i.title}</span>
                                    <span className={`category-badge cat-${i.category.toLowerCase()}`}>{i.category}</span>
                                </div>
                                <div className="issue-list-meta">
                                    <span>Location: {i.location}</span>
                                    <span>Updated: {i.updated_date}</span>
                                </div>
                            </div>
                            <div style={{ flexShrink: 0 }}>
                                <span className={`status-badge status-${i.status.toLowerCase().replace(" ", "-")}`}>{i.status}</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

// ─── Announcements Page ───────────────────────────────────────────────────────

function AnnouncementsPage({ token, user }) {
    const isAdmin = user && user.role === "Admin";

    const [view, setView] = React.useState("list");
    const [announcements, setAnnouncements] = React.useState([]);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState("");
    const [selected, setSelected] = React.useState(null);

    const [formTitle, setFormTitle] = React.useState("");
    const [formContent, setFormContent] = React.useState("");
    const [formCategory, setFormCategory] = React.useState("General");
    const [formCategoryOther, setFormCategoryOther] = React.useState("");
    const [formStatus, setFormStatus] = React.useState("published");
    const [formError, setFormError] = React.useState("");
    const [saving, setSaving] = React.useState(false);

    const fetchAnnouncements = () => {
        setLoading(true);
        apiFetch("/api/announcements", token)
            .then(data => { setAnnouncements(data); setLoading(false); })
            .catch(err => { setError(err.message); setLoading(false); });
    };

    React.useEffect(() => { fetchAnnouncements(); }, []);

    const openAdd = () => {
        setFormTitle(""); setFormContent(""); setFormCategory("General"); setFormCategoryOther(""); setFormStatus("published"); setFormError("");
        setView("add");
    };

    const openEdit = (ann) => {
        setSelected(ann);
        const knownAnnCats = ANNOUNCEMENT_CATEGORIES;
        setFormTitle(ann.title); setFormContent(ann.content);
        setFormCategory(knownAnnCats.includes(ann.category) ? ann.category : "Other");
        setFormCategoryOther(knownAnnCats.includes(ann.category) ? "" : ann.category);
        setFormStatus(ann.status); setFormError("");
        setView("edit");
    };

    const handleSave = (e) => {
        e.preventDefault(); setFormError("");
        if (!formTitle.trim() || !formContent.trim()) { setFormError("Title and content are required."); return; }
        if (formCategory === "Other" && !formCategoryOther.trim()) { setFormError("Please enter a category name."); return; }
        setSaving(true);
        const effectiveCat = formCategory === "Other" ? formCategoryOther.trim() : formCategory;
        const isEdit = view === "edit";
        apiFetch(isEdit ? `/api/announcements/${selected.id}` : "/api/announcements", token, {
            method: isEdit ? "PUT" : "POST",
            body: JSON.stringify({ title: formTitle, content: formContent, category: effectiveCat, status: formStatus })
        })
            .then(() => {
                setSaving(false);
                fetchAnnouncements();
                setView("list"); setSelected(null);
            })
            .catch(err => { setFormError(err.message); setSaving(false); });
    };

    const handleArchive = (ann) => {
        if (!window.confirm(`Archive "${ann.title}"?`)) return;
        apiFetch(`/api/announcements/${ann.id}`, token, {
            method: "PUT",
            body: JSON.stringify({ title: ann.title, content: ann.content, category: ann.category, status: "archived" })
        })
            .then(() => { fetchAnnouncements(); setView("list"); setSelected(null); })
            .catch(err => { setError(err.message); });
    };

    if (view === "add" || view === "edit") {
        return (
            <div className="card">
                <button className="btn-back" onClick={() => setView(view === "edit" ? "detail" : "list")}>
                    {view === "edit" ? "Cancel Edit" : "Back to Announcements"}
                </button>
                <h2>{view === "edit" ? "Edit Announcement" : "New Announcement"}</h2>
                {formError && <div className="error-panel">{formError}</div>}
                <form onSubmit={handleSave}>
                    <div className="form-group">
                        <label>Title</label>
                        <input type="text" value={formTitle} onChange={e => setFormTitle(e.target.value)} placeholder="Announcement title" />
                    </div>
                    <div className="form-group">
                        <label>Category</label>
                        <select value={formCategory} onChange={e => { setFormCategory(e.target.value); setFormCategoryOther(""); }} className="form-select">
                            {ANNOUNCEMENT_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                        {formCategory === "Other" && (
                            <input type="text" value={formCategoryOther} onChange={e => setFormCategoryOther(e.target.value)} placeholder="Enter category name" style={{ marginTop: "0.5rem" }} />
                        )}
                    </div>
                    <div className="form-group">
                        <label>Content</label>
                        <textarea value={formContent} onChange={e => setFormContent(e.target.value)} rows="7" className="form-textarea" placeholder="Announcement details..." />
                    </div>
                    {view === "edit" && (
                        <div className="form-group">
                            <label>Status</label>
                            <select value={formStatus} onChange={e => setFormStatus(e.target.value)} className="form-select">
                                <option value="published">Published</option>
                                <option value="archived">Archived</option>
                            </select>
                        </div>
                    )}
                    <button type="submit" className="btn-primary" disabled={saving}>
                        {saving ? "Saving..." : (view === "edit" ? "Save Changes" : "Publish Announcement")}
                    </button>
                </form>
            </div>
        );
    }

    if (view === "detail" && selected) {
        const ann = announcements.find(a => a.id === selected.id) || selected;
        return (
            <div className="card">
                <button className="btn-back" onClick={() => { setView("list"); setSelected(null); }}>Back to Announcements</button>
                <div className="rec-detail-header">
                    <div>
                        <h2>{ann.title}</h2>
                        <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.375rem", alignItems: "center" }}>
                            <span className={`category-badge cat-ann-${ann.category.toLowerCase()}`}>{ann.category}</span>
                            {ann.status === "archived" && <span className="archived-label">Archived</span>}
                        </div>
                    </div>
                    {isAdmin && (
                        <div style={{ display: "flex", gap: "0.5rem", flexShrink: 0 }}>
                            <button className="btn-primary btn-sm" style={{ width: "auto" }} onClick={() => openEdit(ann)}>Edit</button>
                            {ann.status !== "archived" && (
                                <button className="btn-danger-outline btn-sm" onClick={() => handleArchive(ann)}>Archive</button>
                            )}
                        </div>
                    )}
                </div>
                <div className="detail-grid">
                    <div className="detail-row detail-description">
                        <strong>Details</strong>
                        <span style={{ whiteSpace: "pre-wrap" }}>{ann.content}</span>
                    </div>
                    <div className="detail-row"><strong>Published</strong><span>{ann.published_date}</span></div>
                </div>
            </div>
        );
    }

    const visible = isAdmin ? announcements : announcements.filter(a => a.status === "published");

    return (
        <div className="card">
            <div className="section-header">
                <h2>Announcements</h2>
                {isAdmin && <button className="btn-primary btn-sm" onClick={openAdd}>+ New</button>}
            </div>
            <p className="info-text">Community announcements from the management team.</p>
            {loading && <p className="loading-text">Loading announcements...</p>}
            {error && <div className="error-panel">{error}</div>}
            {!loading && !error && visible.length === 0 && <div className="empty-state">No announcements at this time.</div>}
            {!loading && visible.length > 0 && (
                <div className="list">
                    {visible.map(ann => (
                        <div key={ann.id} className="list-item" onClick={() => { setSelected(ann); setView("detail"); }}>
                            <div className="list-item-main">
                                <div className="rec-card-header">
                                    <span className="list-item-title">{ann.title}</span>
                                    <span className={`category-badge cat-ann-${ann.category.toLowerCase()}`}>{ann.category}</span>
                                    {isAdmin && ann.status === "archived" && <span className="archived-label">archived</span>}
                                </div>
                                <span className="list-item-sub">{ann.published_date}</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

// ─── Announcements Dashboard Widget ──────────────────────────────────────────

function AnnouncementsWidget({ token, onNavigate }) {
    const [items, setItems] = React.useState([]);
    const [loading, setLoading] = React.useState(true);

    React.useEffect(() => {
        apiFetch("/api/announcements", token)
            .then(data => {
                setItems(data.filter(a => a.status === "published").slice(0, 3));
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, []);

    return (
        <div className="dashboard-widget">
            <div className="dashboard-widget-header">
                <h3>Latest Announcements</h3>
                <button className="btn-secondary" style={{ fontSize: "0.8rem" }} onClick={() => onNavigate("announcements")}>View all</button>
            </div>
            {loading && <p className="loading-text" style={{ margin: "0.5rem 0" }}>Loading...</p>}
            {!loading && items.length === 0 && (
                <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", margin: 0 }}>No announcements at this time.</p>
            )}
            {!loading && items.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                    {items.map(ann => (
                        <div key={ann.id} className="announcement-widget-item" onClick={() => onNavigate("announcements")}>
                            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                                <span style={{ fontWeight: 600, fontSize: "0.9rem", flex: 1 }}>{ann.title}</span>
                                <span className={`category-badge cat-ann-${ann.category.toLowerCase()}`}>{ann.category}</span>
                            </div>
                            <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>{ann.published_date}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function renderAgentText(text) {
    const lines = String(text || "").split("\n");

    return lines.map((line, lineIndex) => (
        <React.Fragment key={lineIndex}>
            {line.split(/(\*\*[^*]+\*\*)/g).map((part, partIndex) => {
                const isBold = part.startsWith("**") && part.endsWith("**");
                return isBold
                    ? <strong key={partIndex}>{part.slice(2, -2)}</strong>
                    : <React.Fragment key={partIndex}>{part}</React.Fragment>;
            })}
            {lineIndex < lines.length - 1 && <br />}
        </React.Fragment>
    ));
}

// ─── App Root ─────────────────────────────────────────────────────────────────

function CommUnityAgent({ token, user, onClose }) {
    const [messages, setMessages] = React.useState([
        { role: "agent", text: `Hi ${user.name.split(" ")[0]}! I'm the CommUnity Agent. Ask me about contacts, recommendations, announcements, or your issues.` }
    ]);
    const [input, setInput] = React.useState("");
    const [sessionId, setSessionId] = React.useState(null);
    const [busy, setBusy] = React.useState(false);
    const [error, setError] = React.useState("");

    const sendMessage = async (event) => {
        event.preventDefault();
        const text = input.trim();
        if (!text || busy) return;
        setError("");
        setMessages(prev => [...prev, { role: "user", text }]);
        setInput(""); setBusy(true);
        try {
            const data = await apiFetch("/api/agent/chat", token, {
                method: "POST",
                body: JSON.stringify({ message: text, session_id: sessionId })
            });
            setSessionId(data.session_id);
            setMessages(prev => [...prev, { role: "agent", text: data.response }]);
        } catch (err) {
            setError(err.message || "Agent request failed.");
        } finally { setBusy(false); }
    };

    return (
        <div className="agent-overlay" onClick={onClose}>
            <section className="agent-panel" onClick={e => e.stopPropagation()} aria-label="CommUnity Agent">
                <div className="agent-header">
                    <div><strong>✨ CommUnity Agent</strong><span>Community information and actions</span></div>
                    <button className="agent-close" onClick={onClose} aria-label="Close agent">×</button>
                </div>
                <div className="agent-messages">
                    {messages.map((m, i) => (
                        <div key={i} className={`agent-message ${m.role}`}>
                            {renderAgentText(m.text)}
                        </div>
                    ))}
                    {busy && <div className="agent-message agent">Thinking…</div>}
                </div>
                {error && <div className="agent-error">{error}</div>}
                <form className="agent-input-row" onSubmit={sendMessage}>
                    <input value={input} onChange={e => setInput(e.target.value)} placeholder="Ask CommUnity Agent…" disabled={busy} />
                    <button type="submit" className="btn-primary btn-sm" disabled={busy || !input.trim()}>Send</button>
                </form>
                <div className="agent-hint">Writes require your explicit confirmation.</div>
            </section>
        </div>
    );
}

function App() {
    const [token, setToken] = React.useState(localStorage.getItem("token") || null);
    const [user, setUser] = React.useState(null);
    const [loading, setLoading] = React.useState(!!token);
    const [currentPage, setCurrentPage] = React.useState(token ? "dashboard" : "login");
    const [menuOpen, setMenuOpen] = React.useState(false);
    const [agentOpen, setAgentOpen] = React.useState(false);

    const [loginEmail, setLoginEmail] = React.useState("");
    const [loginPassword, setLoginPassword] = React.useState("");
    const [loginError, setLoginError] = React.useState("");
    const [loginSuccess, setLoginSuccess] = React.useState("");

    const [signupName, setSignupName] = React.useState("");
    const [signupEmail, setSignupEmail] = React.useState("");
    const [signupFlat, setSignupFlat] = React.useState("");
    const [signupPassword, setSignupPassword] = React.useState("");
    const [signupConfirmPassword, setSignupConfirmPassword] = React.useState("");
    const [signupError, setSignupError] = React.useState("");

    React.useEffect(() => {
        if (token) {
            setLoading(true);
            apiFetch("/api/auth/me", token)
                .then(profile => { setUser(profile); setLoading(false); })
                .catch(() => {
                    localStorage.removeItem("token");
                    setToken(null); setUser(null);
                    setCurrentPage("login"); setLoading(false);
                });
        } else {
            setUser(null); setLoading(false);
        }
    }, [token]);

    const handleLogin = (e) => {
        e.preventDefault(); setLoginError("");
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
            .catch(err => {
                setLoginEmail(""); setLoginPassword("");
                setLoginError(err.message || "Invalid email or password.");
            });
    };

    const handleSignup = (e) => {
        e.preventDefault(); setSignupError("");
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
                setSignupName(""); setSignupEmail(""); setSignupFlat(""); setSignupPassword(""); setSignupConfirmPassword("");
                setLoginEmail(""); setLoginPassword(""); setLoginError("");
                setLoginSuccess("Account registered successfully! Please log in.");
                setCurrentPage("login");
            })
            .catch(err => setSignupError(err.message));
    };

    const handleLogout = () => {
        localStorage.removeItem("token");
        setToken(null); setUser(null); setCurrentPage("login");
    };

    const renderContent = () => {
        if (loading) return <div className="card" style={{ textAlign: "center", padding: "3rem" }}><p>Loading...</p></div>;

        if (!user) {
            if (currentPage === "signup") {
                return (
                    <div className="card">
                        <h2>Create CommUnity Account</h2>
                        <p className="welcome-text">Join your residential community portal.</p>
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
                    {loginError && <div className="error-panel">{loginError}</div>}
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
                    </div>
                );
            case "contacts":
                return <ContactsPage token={token} />;
            case "recommendations":
                return <RecommendationsPage token={token} user={user} />;
            case "issues":
                return <IssuesPage token={token} user={user} />;
            case "announcements":
                return <AnnouncementsPage token={token} user={user} />;
            case "profile":
                return (
                    <div className="card">
                        <h2>Resident Profile</h2>
                        <p className="info-text">Your account details and role information.</p>
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
                            ["dashboard", "Dashboard"],
                            ["contacts", "Contacts"],
                            ["recommendations", "Recommendations"],
                            ["issues", "Issues"],
                            ["announcements", "Announcements"]
                        ].map(([page, label]) => (
                            <button key={page}
                                className={`nav-link ${currentPage === page ? "active" : ""}`}
                                onClick={() => setCurrentPage(page)}
                            >{label}</button>
                        ))}
                    </nav>
                )}
                {user && (
                    <div className="header-actions">
                        <button className="agent-trigger" onClick={() => { setAgentOpen(true); setMenuOpen(false); }}>✨ CommUnity Agent</button>
                        <div className="user-menu-container">
                            <button className="user-menu-trigger" onClick={() => setMenuOpen(!menuOpen)}>
                                👤 {user.name} ({user.flat_number}) <span className="arrow">▼</span>
                            </button>
                            {menuOpen && (
                                <div className="user-dropdown">
                                    <button className="dropdown-item" onClick={() => { setCurrentPage("profile"); setMenuOpen(false); }}>Profile</button>
                                    <button className="dropdown-item" onClick={() => { handleLogout(); setMenuOpen(false); }}>Logout</button>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </header>
            <main className="main-content">
                {renderContent()}
            </main>
            {user && agentOpen && <CommUnityAgent token={token} user={user} onClose={() => setAgentOpen(false)} />}
            <footer className="footer">
                <p>&copy; 2026 CommUnity Platform. All rights reserved.</p>
            </footer>
        </div>
    );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
