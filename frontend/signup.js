const API = '';
const GRADES = ['A+','A','A-','B+','B','B-','C+','C','C-','D+','D','D-','F'];

let allCourses = [];

async function loadCourses() {
  try {
    const res = await fetch(`${API}/courses/`);
    if (res.ok) allCourses = await res.json();
  } catch (_) {}
}

function buildCourseOptions(excludeCodes = []) {
  const excludeSet = new Set(excludeCodes);
  return allCourses
    .filter(c => !excludeSet.has(c.code))
    .map(c => `<option value="${c.code}">${c.code} – ${c.name}</option>`)
    .join('');
}

function getUsedCodes() {
  const codes = [];
  document.querySelectorAll('.course-select').forEach(sel => {
    if (sel.value) codes.push(sel.value);
  });
  return codes;
}

function refreshAllSelects() {
  const used = getUsedCodes();
  document.querySelectorAll('.course-select').forEach(sel => {
    const current = sel.value;
    const others = used.filter(c => c !== current);
    sel.innerHTML = `<option value="">-- Select Course --</option>` + buildCourseOptions(others);
    sel.value = current;
  });
}

function addCompletedRow() {
  const container = document.getElementById('completedCoursesList');
  const used = getUsedCodes();
  const row = document.createElement('div');
  row.className = 'course-row with-grade';
  row.innerHTML = `
    <select class="course-select" onchange="refreshAllSelects()">
      <option value="">-- Select Course --</option>
      ${buildCourseOptions(used)}
    </select>
    <select class="grade-select">
      ${GRADES.map(g => `<option value="${g}">${g}</option>`).join('')}
    </select>
    <button type="button" class="btn-remove-row" title="Remove" onclick="removeRow(this)">
      <i class="fas fa-times"></i>
    </button>`;
  container.appendChild(row);
}

function addEnrolledRow() {
  const container = document.getElementById('enrolledCoursesList');
  const used = getUsedCodes();
  const row = document.createElement('div');
  row.className = 'course-row no-grade';
  row.innerHTML = `
    <select class="course-select" onchange="refreshAllSelects()">
      <option value="">-- Select Course --</option>
      ${buildCourseOptions(used)}
    </select>
    <button type="button" class="btn-remove-row" title="Remove" onclick="removeRow(this)">
      <i class="fas fa-times"></i>
    </button>`;
  container.appendChild(row);
}


function removeRow(btn) {
  btn.closest('.course-row').remove();
  refreshAllSelects();
}

function showError(msg) {
  const el = document.getElementById('signupError');
  el.textContent = msg;
  el.style.display = 'block';
  document.getElementById('signupSuccess').style.display = 'none';
}

function showSuccess(msg) {
  const el = document.getElementById('signupSuccess');
  el.textContent = msg;
  el.style.display = 'block';
  document.getElementById('signupError').style.display = 'none';
}

async function submitSignup() {
  const btn = document.getElementById('signupBtn');
  document.getElementById('signupError').style.display = 'none';
  document.getElementById('signupSuccess').style.display = 'none';

  const firstName   = document.getElementById('firstName').value.trim();
  const lastName    = document.getElementById('lastName').value.trim();
  const email       = document.getElementById('email').value.trim();
  const universityId = document.getElementById('universityId').value.trim();
  const phone       = document.getElementById('phone').value.trim();
  const password    = document.getElementById('password').value;

  if (!firstName || !lastName || !email || !universityId || !phone || !password) {
    showError('Please fill in all required personal information fields.');
    return;
  }

  // Collect completed courses
  const completedCourses = [];
  let hasEmptyCompleted = false;
  document.querySelectorAll('#completedCoursesList .course-row').forEach(row => {
    const code  = row.querySelector('.course-select').value;
    const grade = row.querySelector('.grade-select').value;
    if (!code) { hasEmptyCompleted = true; return; }
    completedCourses.push({ course_code: code, grade });
  });
  if (hasEmptyCompleted) {
    showError('Please select a course for every completed course entry, or remove the empty row.');
    return;
  }

  // Collect enrolled courses
  const currentEnrolled = [];
  let hasEmptyEnrolled = false;
  document.querySelectorAll('#enrolledCoursesList .course-row').forEach(row => {
    const code = row.querySelector('.course-select').value;
    if (!code) { hasEmptyEnrolled = true; return; }
    currentEnrolled.push(code);
  });
  if (hasEmptyEnrolled) {
    showError('Please select a course for every enrolled course entry, or remove the empty row.');
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin" style="margin-right:8px"></i>Creating Account…';

  try {
    const res = await fetch(`${window.location.origin}/signup`, {
    method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        first_name: firstName,
        last_name: lastName,
        email,
        university_id: universityId,
        phone_number: phone,
        password,
        completed_courses: completedCourses,
        current_enrolled: currentEnrolled,
      }),
    });

    const data = await res.json();

    if (res.ok) {
      showSuccess(data.message + ' Redirecting to login…');
      btn.disabled = true;
      setTimeout(() => { window.location.href = 'index.html'; }, 2000);
    } else {
      showError(data.detail || 'Sign-up failed. Please try again.');
      btn.disabled = false;
      btn.innerHTML = '<i class="fas fa-user-check" style="margin-right:8px"></i>Create Account';
    }
  } catch (_) {
    showError('Could not connect to the server. Please make sure the backend is running.');
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-user-check" style="margin-right:8px"></i>Create Account';
  }
}

loadCourses();
