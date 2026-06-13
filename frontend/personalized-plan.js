// Personalized Plan – Generates and renders an optimal graduation plan
(function () {
  const generateBtn = document.getElementById('generateBtn');
  const generateSection = document.getElementById('generateSection');
  const loadingState = document.getElementById('loadingState');
  const planStats = document.getElementById('planStats');
  const planContainer = document.getElementById('planContainer');
  const printSection = document.getElementById('printSection');
  const printBtn = document.getElementById('printBtn');

  const studentId = localStorage.getItem('student_id') || '';

  if (!generateBtn) return;

  // ── Plan type colors ──────────────────────────────────────────────────────
  function getTypeStyle(planType) {
    const t = (planType || '').toLowerCase();
    if (t.includes('university compulsory')) return { bg: '#eff6ff', border: '#bfdbfe', color: '#1d4ed8', icon: 'fa-university' };
    if (t.includes('faculty compulsory'))    return { bg: '#f0fdf4', border: '#86efac', color: '#166534', icon: 'fa-building-columns' };
    if (t.includes('department compulsory')) return { bg: '#fefce8', border: '#fde047', color: '#854d0e', icon: 'fa-graduation-cap' };
    if (t.includes('department elective'))   return { bg: '#faf5ff', border: '#d8b4fe', color: '#7c3aed', icon: 'fa-puzzle-piece' };
    if (t.includes('university elective'))   return { bg: '#fff7ed', border: '#fed7aa', color: '#c2410c', icon: 'fa-book-open' };
    return { bg: 'var(--gray-50)', border: 'var(--gray-200)', color: 'var(--gray-600)', icon: 'fa-book' };
  }

  // ── Semester type icon + gradient ─────────────────────────────────────────
  function getSemesterStyle(semType) {
    switch (semType) {
      case 'Fall':   return { icon: 'fa-leaf',      gradient: 'linear-gradient(135deg, #f97316, #ea580c)', iconColor: '#f97316' };
      case 'Spring': return { icon: 'fa-seedling',   gradient: 'linear-gradient(135deg, #22c55e, #16a34a)', iconColor: '#22c55e' };
      case 'Summer': return { icon: 'fa-sun',        gradient: 'linear-gradient(135deg, #eab308, #ca8a04)', iconColor: '#eab308' };
      default:       return { icon: 'fa-calendar',   gradient: 'linear-gradient(135deg, #6366f1, #4f46e5)', iconColor: '#6366f1' };
    }
  }

  // ── Generate Plan ─────────────────────────────────────────────────────────
  generateBtn.addEventListener('click', async () => {
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
    loadingState.style.display = 'flex';
    planContainer.innerHTML = '';
    planStats.style.display = 'none';
    printSection.style.display = 'none';

    try {
      const res = await fetch(`/personalized-plan/${studentId}/generate`);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to generate plan');
      }

      const data = await res.json();
      loadingState.style.display = 'none';

      if (data.message) {
        // Already completed all courses
        planContainer.innerHTML = `
          <div class="pp-empty">
            <i class="fas fa-party-horn" style="font-size: 48px; color: var(--yellow); margin-bottom: 16px;"></i>
            <h2>🎉 ${data.message}</h2>
            <p style="color: var(--gray-500); margin-top: 8px;">You've completed all required courses. Way to go!</p>
          </div>`;
        generateSection.style.display = 'none';
        return;
      }

      // ── Stats bar ───────────────────────────────────────────────────────
      const totalPlanHours = data.plan.reduce((s, sem) => s + sem.total_hours, 0);
      const totalPlanCourses = data.plan.reduce((s, sem) => s + sem.courses.length, 0);

      planStats.style.display = 'flex';
      planStats.className = 'pp-stats';
      planStats.innerHTML = `
        <div class="pp-stat-card">
          <div class="pp-stat-icon" style="background: rgba(34,197,94,.1); color: #22c55e;"><i class="fas fa-check-circle"></i></div>
          <div>
            <div class="pp-stat-value">${data.completed_credits}</div>
            <div class="pp-stat-label">Credits Completed</div>
          </div>
        </div>
        <div class="pp-stat-card">
          <div class="pp-stat-icon" style="background: rgba(234,179,8,.1); color: #eab308;"><i class="fas fa-spinner"></i></div>
          <div>
            <div class="pp-stat-value">${data.enrolled_credits}</div>
            <div class="pp-stat-label">Currently Enrolled</div>
          </div>
        </div>
        <div class="pp-stat-card">
          <div class="pp-stat-icon" style="background: rgba(59,130,246,.1); color: #3b82f6;"><i class="fas fa-book-open"></i></div>
          <div>
            <div class="pp-stat-value">${data.remaining_credits}</div>
            <div class="pp-stat-label">Credits Remaining</div>
          </div>
        </div>
        <div class="pp-stat-card">
          <div class="pp-stat-icon" style="background: rgba(99,102,241,.1); color: #6366f1;"><i class="fas fa-calendar-alt"></i></div>
          <div>
            <div class="pp-stat-value">${data.total_semesters}</div>
            <div class="pp-stat-label">Semesters to Go</div>
          </div>
        </div>
      `;

      // ── Render plan timeline ────────────────────────────────────────────
      renderPlan(data.plan);

      // Show print button
      printSection.style.display = 'block';

      // Change button text
      generateSection.style.display = 'block';
      generateBtn.disabled = false;
      generateBtn.innerHTML = '<i class="fas fa-arrows-rotate"></i> Regenerate Plan';

    } catch (err) {
      loadingState.style.display = 'none';
      planContainer.innerHTML = `
        <div class="pp-error">
          <i class="fas fa-exclamation-triangle"></i>
          <p>${err.message}</p>
        </div>`;
      generateBtn.disabled = false;
      generateBtn.innerHTML = '<i class="fas fa-wand-magic-sparkles"></i> Generate My Personalized Plan';
    }
  });

  // ── Render plan ───────────────────────────────────────────────────────────
  function renderPlan(plan) {
    planContainer.innerHTML = '';

    const timeline = document.createElement('div');
    timeline.className = 'pp-timeline';

    plan.forEach((sem, idx) => {
      const semStyle = getSemesterStyle(sem.semester_type);
      const isLast = idx === plan.length - 1;

      const block = document.createElement('div');
      block.className = 'pp-semester animate-in';
      block.style.animationDelay = `${idx * 0.08}s`;

      block.innerHTML = `
        <div class="pp-semester__connector">
          <div class="pp-semester__dot" style="background: ${semStyle.gradient};">
            <i class="fas ${semStyle.icon}"></i>
          </div>
          ${!isLast ? '<div class="pp-semester__line"></div>' : ''}
        </div>
        <div class="pp-semester__content">
          <div class="pp-semester__header">
            <div>
              <h3 class="pp-semester__title">${sem.semester_label}</h3>
              <span class="pp-semester__meta">${sem.courses.length} course${sem.courses.length !== 1 ? 's' : ''} · ${sem.total_hours} credit hours</span>
            </div>
            <div class="pp-semester__badge">${sem.total_hours} hrs</div>
          </div>
          <div class="pp-semester__grid">
            ${sem.courses.map(c => {
              const ts = getTypeStyle(c.plan_type);
              return `
                <div class="pp-course" style="background: ${ts.bg}; border-color: ${ts.border};">
                  <div class="pp-course__top">
                    <span class="pp-course__code" style="color: ${ts.color};"><i class="fas ${ts.icon}" style="margin-right: 4px; font-size: 10px;"></i>${c.course_code}</span>
                    <span class="pp-course__cr">${c.credit_hours} CH</span>
                  </div>
                  <div class="pp-course__name">${c.course_name}</div>
                  ${c.prerequisites && c.prerequisites !== 'None'
                    ? `<div class="pp-course__prereq"><i class="fas fa-link" style="margin-right: 3px;"></i>${c.prerequisites}</div>`
                    : ''}
                  <div class="pp-course__type">${c.plan_type}</div>
                </div>`;
            }).join('')}
          </div>
        </div>
      `;
      timeline.appendChild(block);
    });

    // Graduation card at the end
    const gradCard = document.createElement('div');
    gradCard.className = 'pp-graduation animate-in';
    gradCard.style.animationDelay = `${plan.length * 0.08}s`;
    gradCard.innerHTML = `
      <div class="pp-semester__connector">
        <div class="pp-semester__dot pp-semester__dot--grad" style="background: linear-gradient(135deg, var(--yellow), #f59e0b);">
          <i class="fas fa-graduation-cap"></i>
        </div>
      </div>
      <div class="pp-graduation__content">
        <h3>🎓 Graduation!</h3>
        <p>If you follow this plan, you'll complete all 132 credit hours and be ready to graduate.</p>
      </div>
    `;
    timeline.appendChild(gradCard);

    planContainer.appendChild(timeline);
  }

  // ── Print ─────────────────────────────────────────────────────────────────
  if (printBtn) {
    printBtn.addEventListener('click', () => {
      window.print();
    });
  }
})();
