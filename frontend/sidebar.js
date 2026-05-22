// Sidebar component – injects sidebar HTML, highlights active page, always dark
(async function() {
  document.body.classList.add('dark-mode');

  const currentPage = window.location.pathname.split('/').pop() || 'index.html';

  // Auth Guard
  const studentId = localStorage.getItem('student_id');
  if (!studentId && currentPage !== 'index.html' && currentPage !== '') {
    window.location.href = '/';
    return;
  }

  // Fetch user info
  let userName = 'Student';
  let displayId = 'ID: Unknown';

  if (studentId) {
    try {
      const res = await fetch(`/student/${studentId}`);
      if (res.ok) {
        const student = await res.json();
        userName = `${student.first_name} ${student.last_name}`;
        displayId = `ID: ${student.university_id}`;
      } else {
        localStorage.removeItem('student_id');
        window.location.href = '/';
        return;
      }
    } catch (err) {
      console.error('Failed to load user info for sidebar');
    }
  }

  const menuItems = [
    { icon: 'fa-comment-dots',      label: 'Active Session', href: '/chatbot', id: 'chatbot' },
    { icon: 'fa-clock-rotate-left', label: 'Chat History',   href: '/history', id: 'history' },
  ];

  const uniLinks = [
    { icon: 'fa-earth-americas', label: 'Course Roadmap',  href: '/roadmap',     id: 'roadmap'     },
    { icon: 'fa-calculator',     label: 'GPA Calculator',  href: '/gpa',         id: 'gpa'         },
    { icon: 'fa-door-open',      label: 'Study Rooms',     href: '/study-rooms', id: 'study-rooms' },
    { icon: 'fa-users',          label: 'Faculty Info',    href: '/faculty',     id: 'faculty'     },
    { icon: 'fa-book',           label: 'Courses Catalog', href: '/courses',     id: 'courses'     },
  ];

  function isActive(href) {
    const clean = href.replace(/^\//, '');
    return currentPage === clean + '.html' || currentPage === clean || window.location.pathname === href;
  }

  function buildItems(items) {
    return items.map(item => {
      const active = isActive(item.href) ? ' active' : '';
      return `<a href="${item.href}" class="menu-item${active}"><i class="fas ${item.icon}"></i>${item.label}</a>`;
    }).join('');
  }

  const sidebarHTML = `
    <div class="sidebar-header">
      <i class="fas fa-robot"></i>
      <div class="brand-text">
        <h3>JUST Advisor</h3>
        <p>Student Portal AI</p>
      </div>
    </div>
    <button class="btn-new" onclick="window.location.href='/chatbot'">
      <i class="fas fa-plus"></i> New Consultation
    </button>
    <div class="menu-label">MENU</div>
    ${buildItems(menuItems)}
    <div class="menu-label" style="margin-top:20px">UNIVERSITY LINKS</div>
    ${buildItems(uniLinks)}
    <div class="sidebar-footer">
      <div class="user-icon"><i class="fas fa-user"></i></div>
      <div class="user-info">
        <div class="user-name">${userName}</div>
        <div class="user-id">${displayId}</div>
      </div>
      <a href="/profile" class="chevron"><i class="fas fa-chevron-right"></i></a>
    </div>
  `;

  const sidebar = document.querySelector('.sidebar');
  if (sidebar) sidebar.innerHTML = sidebarHTML;

  // Top bar (landing pages)
  const topbar = document.querySelector('.top-bar');
  if (topbar) {
    topbar.innerHTML = `
      <div class="tb-brand">
        <div class="dot">J</div>
        <span>JUST Advisor</span>
      </div>
      <div class="tb-links">
        <a href="/">Home</a>
        <a href="/about">About</a>
        <a href="/features">Features</a>
        <button class="btn-ask" onclick="window.location.href='/chatbot'">
          <i class="fas fa-robot"></i> Ask AI Advisor
        </button>
      </div>
    `;
  }

  // Footer
  const footer = document.querySelector('.site-footer');
  if (footer) {
    footer.innerHTML = `
      <div class="footer-inner">
        <div class="footer-top">
          <div class="ft-brand">
            <div class="ft-dot">J</div>
            <span>Jordan University of Science and Technology</span>
          </div>
          <div class="ft-links">
            <a href="#">Privacy Policy</a>
            <a href="#">Terms of Service</a>
            <a href="#">Help Center</a>
          </div>
        </div>
        <div class="footer-bottom">
          <p>&copy; 2025 JUST Academic Advisor. All rights reserved.</p>
        </div>
      </div>
    `;
  }

  // Mobile sidebar toggle
  document.querySelectorAll('.hamburger-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelector('.sidebar')?.classList.toggle('open');
    });
  });

  // PERSISTENT MEETING WIDGET
  function _esc(str) {
    const d = document.createElement('div');
    d.textContent = String(str ?? '');
    return d.innerHTML;
  }

  const activeMeeting = JSON.parse(sessionStorage.getItem('active_meeting') || 'null');
  if (activeMeeting && currentPage !== 'room.html') {
    const widget = document.createElement('div');
    widget.id = 'miniMeetingWidget';
    widget.style.cssText = `
      position:fixed;bottom:20px;right:20px;width:280px;background:#1e293b;
      border-radius:1rem;border:1px solid #3b82f6;box-shadow:0 10px 25px rgba(0,0,0,.5);
      z-index:10001;padding:1rem;color:white;animation:slideIn 0.3s ease-out;
    `;
    widget.innerHTML = `
      <style>
        @keyframes slideIn{from{transform:translateY(100px);opacity:0}to{transform:translateY(0);opacity:1}}
        .mini-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem}
        .mini-title{font-size:.9rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:150px}
        .mini-tag{font-size:.7rem;background:#3b82f6;padding:2px 6px;border-radius:4px}
        .mini-video-preview{width:100%;height:140px;background:#0f172a;border-radius:.5rem;margin-bottom:.8rem;overflow:hidden;position:relative}
        .mini-video-preview video{width:100%;height:100%;object-fit:cover}
        .mini-controls{display:flex;gap:.5rem;margin-top:.8rem}
        .mini-btn{flex:1;padding:.5rem;border-radius:.5rem;border:none;cursor:pointer;font-size:.8rem;font-weight:600;transition:.2s}
        .btn-return{background:#3b82f6;color:white}.btn-return:hover{background:#2563eb}
        .btn-quit{background:rgba(239,68,68,.1);color:#ef4444;border:1px solid #ef4444}.btn-quit:hover{background:#ef4444;color:white}
      </style>
      <div class="mini-header">
        <span class="mini-tag">LIVE PREVIEW</span>
        <span style="background:#10b981;width:8px;height:8px;border-radius:50%;display:inline-block"></span>
      </div>
      <div class="mini-video-preview">
        <video id="miniVideo" autoplay playsinline muted></video>
        <div id="miniPlaceholder" style="position:absolute;top:0;left:0;width:100%;height:100%;display:flex;align-items:center;justify-content:center;flex-direction:column;background:#1e293b">
          <i class="fas fa-video-slash" style="font-size:1.5rem;color:#475569;margin-bottom:.5rem"></i>
          <span style="font-size:.75rem;color:#475569">${_esc(activeMeeting.name)}</span>
        </div>
      </div>
      <div class="mini-title">${_esc(activeMeeting.name)}</div>
      <div class="mini-controls">
        <button class="mini-btn btn-return" id="returnToMeeting">Return</button>
        <button class="mini-btn btn-quit" id="quitMiniMeeting">Leave</button>
      </div>
    `;
    document.body.appendChild(widget);

    const miniVideo = document.getElementById('miniVideo');
    const miniPlaceholder = document.getElementById('miniPlaceholder');
    let miniStream = null;

    if (activeMeeting.cam) {
      navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        .then(stream => { miniStream = stream; miniVideo.srcObject = stream; miniPlaceholder.style.display = 'none'; })
        .catch(() => {});
    }

    document.getElementById('returnToMeeting').addEventListener('click', () => {
      if (miniStream) miniStream.getTracks().forEach(t => t.stop());
      window.location.href = `/room?id=${activeMeeting.id}&type=${activeMeeting.type}`;
    });

    document.getElementById('quitMiniMeeting').addEventListener('click', async () => {
      const fd = new FormData();
      fd.append('room_id', activeMeeting.id);
      fd.append('room_type', activeMeeting.type);
      fd.append('student_id', studentId);
      await fetch('/rooms/leave', { method: 'POST', body: fd });
      sessionStorage.removeItem('active_meeting');
      widget.remove();
    });
  }
})();
