// GPA Calculator Logic
let globalCourses = [];

document.addEventListener('DOMContentLoaded', async () => {
  const studentId = localStorage.getItem('student_id');
  if (studentId) {
    try {
      const studentRes = await fetch(`/student/${studentId}`);
      if (studentRes.ok) {
        const student = await studentRes.json();
        const prevGpaInput = document.getElementById('prevGpa');
        const prevHoursInput = document.getElementById('prevHours');
        const remainHoursInput = document.getElementById('remainHours');
        
        if (prevGpaInput) prevGpaInput.value = student.current_gpa || 0;
        if (prevHoursInput) prevHoursInput.value = student.completed_credits || 0;
        if (remainHoursInput) remainHoursInput.value = student.remaining_credits || 132;
        
        updateProjector();
      }
    } catch(err) { console.error("Failed to load student data for GPA calculator", err); }
  }

  try {
    const res = await fetch('/courses/');
    if (res.ok) {
      globalCourses = await res.json();
      const dataList = document.createElement('datalist');
      dataList.id = 'courseList';
      globalCourses.forEach(c => {
        const opt = document.createElement('option');
        opt.value = `${c.code} - ${c.name}`;
        dataList.appendChild(opt);
      });
      document.body.appendChild(dataList);
      
      // Bind to existing rows
      document.querySelectorAll('#courseRows input[type="text"]').forEach(input => {
        input.setAttribute('list', 'courseList');
        input.addEventListener('change', handleCourseSelect);
      });
    }
  } catch(e) { console.error(e); }
});

function handleCourseSelect(e) {
  const val = e.target.value;
  const codeMatch = val.split(' - ')[0];
  const selectedCourse = globalCourses.find(c => c.code === codeMatch);
  if (selectedCourse) {
    const tr = e.target.closest('tr');
    const creditsSelect = tr.querySelector('.credits-sel');
    if (creditsSelect) {
      creditsSelect.value = selectedCourse.credit_hours || 3;
    }
  }
}
function addCourse() {
  const tbody = document.getElementById('courseRows');
  const row = document.createElement('tr');
  row.innerHTML = `
    <td><input type="text" list="courseList" class="form-input" placeholder="Course Name"/></td>
    <td><select class="form-input credits-sel"><option value="">-</option><option>1</option><option>2</option><option selected>3</option><option>4</option></select></td>
    <td><select class="form-input grade-sel"><option value="">-</option><option value="4.2">A+</option><option value="4.0">A</option><option value="3.75">A-</option><option value="3.5">B+</option><option value="3.25">B</option><option value="3.0">B-</option><option value="2.75">C+</option><option value="2.5">C</option><option value="2.25">C-</option><option value="2.0">D+</option><option value="1.75">D</option><option value="1.5">D-</option><option value="0.5">F</option></select></td>
    <td><button class="del-btn" onclick="deleteRow(this)"><i class="fas fa-trash"></i></button></td>
  `;
  const input = row.querySelector('input[type="text"]');
  input.addEventListener('change', handleCourseSelect);
  tbody.appendChild(row);
}

function deleteRow(btn) {
  const tbody = document.getElementById('courseRows');
  if (tbody.rows.length > 1) btn.closest('tr').remove();
}

function clearCourses() {
  const tbody = document.getElementById('courseRows');
  while (tbody.rows.length > 1) tbody.deleteRow(1);
  const first = tbody.rows[0];
  first.querySelector('input').value = '';
  first.querySelector('.credits-sel').selectedIndex = 3;
  first.querySelector('.grade-sel').selectedIndex = 0;
}

async function calculateGPA() {
  const rows = document.getElementById('courseRows').rows;
  let courses = [];

  for (let row of rows) {
    const credits = parseFloat(row.querySelector('.credits-sel').value) || 0;
    const select = row.querySelector('.grade-sel');
    const grade = select.options[select.selectedIndex].text;
    
    if (grade !== '-' && credits > 0) {
      courses.push({ grade: grade, credit_hours: credits });
    }
  }

  const prevGpa = parseFloat(document.getElementById('prevGpa').value) || 0;
  const prevHours = parseFloat(document.getElementById('prevHours').value) || 0;

  try {
    const res = await fetch('/api/calculate-gpa', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        current_cgpa: prevGpa,
        current_completed_hours: prevHours,
        courses: courses
      })
    });
    
    if (res.ok) {
      const data = await res.json();
      
      document.getElementById('semGpa').textContent = data.semester_gpa.toFixed(2);
      document.getElementById('semBar').style.width = ((data.semester_gpa / 4.2) * 100) + '%';
      
      document.getElementById('cumGpa').textContent = data.new_cgpa.toFixed(2);
      document.getElementById('cumSub').textContent = prevHours > 0 ? `based on ${prevHours} previous credit hours` : '';
      
      updateProjector();
    } else {
      console.error("Backend error calculating GPA");
    }
  } catch(e) { console.error(e); }
}

function updateProjector() {
  const prevGpa = parseFloat(document.getElementById('prevGpa').value) || 0;
  const prevHours = parseFloat(document.getElementById('prevHours').value) || 0;
  const targetGpa = parseFloat(document.getElementById('targetGpa').value) || 3.5;
  const remainHours = parseFloat(document.getElementById('remainHours').value) || 30;
  const totalHours = prevHours + remainHours;

  if (remainHours <= 0) {
    document.getElementById('reqAvg').textContent = 'N/A';
    document.getElementById('reqNote').textContent = 'Remaining hours must be greater than 0.';
    return;
  }

  // Formula: (Target * Total - Current * Completed) / Remaining
  const needed = ((targetGpa * totalHours) - (prevGpa * prevHours)) / remainHours;
  const clamped = Math.min(4.2, Math.max(0, needed));

  document.getElementById('reqAvg').textContent = clamped.toFixed(2);

  let note = '';
  if (needed > 4.2) {
    note = 'This target may not be achievable with remaining hours.';
  } else {
    if (clamped >= 4.0) note = 'You need to average approx. A in your remaining courses.';
    else if (clamped >= 3.75) note = 'You need to average approx. A- in your remaining courses.';
    else if (clamped >= 3.5) note = 'You need to average approx. B+ in your remaining courses.';
    else if (clamped >= 3.25) note = 'You need to average approx. B in your remaining courses.';
    else if (clamped >= 3.0) note = 'You need to average approx. B- in your remaining courses.';
    else if (clamped >= 2.75) note = 'You need to average approx. C+ in your remaining courses.';
    else if (clamped >= 2.5) note = 'You need to average approx. C in your remaining courses.';
    else if (clamped >= 2.25) note = 'You need to average approx. C- in your remaining courses.';
    else if (clamped >= 2.0) note = 'You need to average approx. D+ in your remaining courses.';
    else note = 'You are on track! Keep it up.';
  }

  document.getElementById('reqNote').textContent = note;
}

document.getElementById('targetGpa')?.addEventListener('input', updateProjector);
document.getElementById('remainHours')?.addEventListener('input', updateProjector);
