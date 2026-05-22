// Course Roadmap – Renders grouped by Year + Semester matching the JUST UI design
(async function () {
  const container = document.getElementById('roadmapContainer');
  if (!container) return;

  const studentId = localStorage.getItem('student_id') || '';

  // Status → CSS class + dot color
  const STATUS = {
    'completed':          { cls: 'completed',  dot: '#22c55e', label: 'Completed' },
    'currently enrolled': { cls: 'enrolled',   dot: '#eab308', label: 'Currently Enrolled' },
    'available':          { cls: 'available',  dot: '#3b82f6', label: 'Available' },
    'locked':             { cls: 'locked',     dot: '#6b7280', label: 'Locked' },
  };

  function getCfg(status) {
    return STATUS[(status || '').toLowerCase()] || STATUS['available'];
  }

  // Auto-recalculate real GPA from completed courses on load
  fetch(`/roadmap/${studentId}/recalculate-gpa`).catch(() => {});

  try {
    const res = await fetch(`/roadmap/${studentId}`);
    if (!res.ok) throw new Error('API error');
    const data = await res.json();

    if (!data.length) {
      container.innerHTML = "<p style='text-align:center;padding:2rem;color:var(--gray-400)'>No roadmap data found.</p>";
      return;
    }

    // ── Summary stats ──────────────────────────────────────────────────────────
    const counts = { completed: 0, enrolled: 0, available: 0, locked: 0 };
    data.forEach(c => {
      const k = (c.status || '').toLowerCase().replace(' ', '_').replace('currently_enrolled', 'enrolled');
      if (counts[k] !== undefined) counts[k]++;
      else if ((c.status || '').toLowerCase() === 'currently enrolled') counts.enrolled++;
    });
    // recalc properly
    counts.completed = data.filter(c => (c.status || '').toLowerCase() === 'completed').length;
    counts.enrolled  = data.filter(c => (c.status || '').toLowerCase() === 'currently enrolled').length;
    counts.available = data.filter(c => (c.status || '').toLowerCase() === 'available').length;
    counts.locked    = data.filter(c => (c.status || '').toLowerCase() === 'locked').length;

    const summary = document.createElement('div');
    summary.className = 'rdm-summary';
    summary.innerHTML = `
      <span class="rdm-badge rdm-badge--completed"><span class="rdm-dot" style="background:#22c55e"></span>Completed (${counts.completed})</span>
      <span class="rdm-badge rdm-badge--enrolled"><span class="rdm-dot" style="background:#eab308"></span>Currently Enrolled (${counts.enrolled})</span>
      <span class="rdm-badge rdm-badge--available"><span class="rdm-dot" style="background:#3b82f6"></span>Available (${counts.available})</span>
      <span class="rdm-badge rdm-badge--locked"><span class="rdm-dot" style="background:#6b7280"></span>Locked – Prerequisites Required (${counts.locked})</span>
    `;
    container.appendChild(summary);

    // ── Group by year + semester ────────────────────────────────────────────────
    const groups = {};
    const order  = [];
    data.forEach(c => {
      const yr = c.year || 1;
      const sem = c.semester || 'Fall';
      const key = `Year ${yr} - ${sem}`;
      if (!groups[key]) { groups[key] = []; order.push({ key, yr, sem }); }
      groups[key].push(c);
    });

    // Deduplicate order & sort: year ASC, Fall before Spring
    const seen = new Set();
    const sortedOrder = order
      .filter(o => { if (seen.has(o.key)) return false; seen.add(o.key); return true; })
      .sort((a, b) => a.yr !== b.yr ? a.yr - b.yr : (a.sem === 'Fall' ? -1 : 1));

    // ── Render each semester block ─────────────────────────────────────────────
    sortedOrder.forEach(({ key }) => {
      const courses = groups[key];
      const totalCR = courses.reduce((s, c) => s + (parseInt(c.credit_hours) || 0), 0);

      const block = document.createElement('div');
      block.className = 'rdm-block animate-in';
      block.innerHTML = `
        <div class="rdm-block__header">
          <h2 class="rdm-block__title">${key}</h2>
        </div>
        <div class="rdm-grid">
          ${courses.map(c => {
            const cfg = getCfg(c.status);
            const hasPrereq = c.prerequisites && c.prerequisites !== 'None';
            const isCompleted = (c.status || '').toLowerCase() === 'completed';
            const gradeCorner = isCompleted && c.grade
              ? `<span class="rdm-card__grade-corner">${c.grade}</span>`
              : '';
            return `
              <div class="rdm-card rdm-card--${cfg.cls}">
                <div class="rdm-card__top">
                  <span class="rdm-card__dot" style="background:${cfg.dot}"></span>
                  <span class="rdm-card__code">${c.course_code}</span>
                  <span class="rdm-card__cr">${c.credit_hours}/${c.credit_hours}</span>
                </div>
                <div class="rdm-card__name">${c.course_name}</div>
                ${hasPrereq ? `<div class="rdm-card__prereq">Prerequisites: ${c.prerequisites}</div>` : ''}
                ${gradeCorner}
              </div>`;
          }).join('')}
        </div>
        <div class="rdm-block__total">Total Cost: ${totalCR}</div>
      `;
      container.appendChild(block);
    });

  } catch (err) {
    console.error(err);
    container.innerHTML = "<p style='text-align:center;padding:2rem;color:#ef4444'>Failed to load roadmap. Make sure the backend is running.</p>";
  }
})();
