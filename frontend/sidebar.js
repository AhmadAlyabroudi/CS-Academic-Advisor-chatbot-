// Sidebar component – injects sidebar HTML and highlights the active page
(async function() {
  // Dark mode is always on
  document.body.classList.add('dark-mode');

  const path = window.location.pathname;
  // Normalise: strip trailing slash, strip .html extension for legacy files
  const currentPage = path.replace(/\.html$/, '').replace(/\/$/, '') || '/';

  // Auth Guard
  const studentId = localStorage.getItem('student_id');
  const publicPages = ['/', '/index', ''];
  if (!studentId && !publicPages.includes(currentPage)) {
    window.location.href = '/';
    return;
  }

  // Fetch user info
  let userName  = 'Student';
  let displayId = 'ID: Unknown';

  if (studentId) {
    try {
      const res = await fetch(`/student/${studentId}`);
      if (res.ok) {
        const student = await res.json();
        userName  = `${student.first_name} ${student.last_name}`;
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
    { icon: 'fa-comment-dots', label: 'Active Session',     href: '/chatbot',     id: 'chatbot'  },
    { icon: 'fa-clock-rotate-left', label: 'Chat History',  href: '#',            id: 'history'  },
  ];

  const uniLinks = [
    { icon: 'fa-earth-americas', label: 'Course Roadmap',   href: '/roadmap',     id: 'roadmap'  },
    { icon: 'fa-calculator',     label: 'GPA Calculator',   href: '/gpa',         id: 'gpa'      },
    { icon: 'fa-door-open',      label: 'Study Rooms',      href: '/study-rooms', id: 'study-rooms' },
    { icon: 'fa-users',          label: 'Faculty Info',     href: '/faculty',     id: 'faculty'  },
    { icon: 'fa-book',           label: 'Courses Catalog',  href: '/courses',     id: 'courses'  },
  ];

  function isActive(href) {
    if (href === '#') return false;
    const normalised = href.replace(/\.html$/, '').replace(/\/$/, '') || '/';
    return currentPage === normalised;
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
    <div class="menu-label" style="margin-top:16px">UNIVERSITY LINKS</div>
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

  // Top bar
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
          <p>&copy; 2025 JUST Advisor. All rights reserved.</p>
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
  const activeMeeting = JSON.parse(sessionStorage.getItem('active_meeting'));
  if (activeMeeting && !currentPage.includes('/room')) {
    const widget = document.createElement('div');
    widget.id = 'miniMeetingWidget';
    widget.style.cssText = `
      position:fixed;bottom:20px;right:20px;width:284px;
      background:#1a1a1a;border-radius:16px;
      border:1px solid #42A5F5;
      box-shadow:0 12px 40px rgba(0,0,0,0.7);
      z-index:10001;padding:16px;color:#EDEDED;
      animation:slideIn .3s ease-out;
    `;
    widget.innerHTML = `
      <style>
        @keyframes slideIn{from{transform:translateY(100px);opacity:0}to{transform:translateY(0);opacity:1}}
        .mini-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:.6rem}
        .mini-title{font-size:.85rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:160px}
        .mini-tag{font-size:.68rem;background:#1e3a5f;color:#90CAF9;padding:2px 8px;border-radius:6px;border:1px solid rgba(66,165,245,.3)}
        .mini-video-preview{width:100%;height:130px;background:#0a0a0a;border-radius:10px;margin-bottom:.8rem;overflow:hidden;position:relative}
        .mini-video-preview video{width:100%;height:100%;object-fit:cover}
        .mini-controls{display:flex;gap:.5rem;margin-top:.6rem}
        .mini-btn{flex:1;padding:.5rem;border-radius:8px;border:none;cursor:pointer;font-size:.78rem;font-weight:700;transition:.2s}
        .btn-return{background:#42A5F5;color:#0a0a0a}
        .btn-return:hover{background:#64B5F6}
        .btn-quit{background:rgba(239,68,68,.1);color:#EF9A9A;border:1px solid rgba(239,68,68,.3)}
        .btn-quit:hover{background:#EF5350;color:#fff}
      </style>
      <div class="mini-header">
        <span class="mini-tag">LIVE PREVIEW</span>
        <div style="display:flex;align-items:center;gap:5px;color:#81C784;font-size:.78rem">
          <span style="width:7px;height:7px;border-radius:50%;background:#4CAF50;display:inline-block;animation:pulse 1.5s infinite"></span>
          Live
        </div>
      </div>
      <div class="mini-video-preview">
        <video id="miniVideo" autoplay playsinline muted></video>
        <div id="miniPlaceholder" style="position:absolute;top:0;left:0;width:100%;height:100%;display:flex;align-items:center;justify-content:center;flex-direction:column;background:#111">
          <i class="fas fa-video-slash" style="font-size:1.4rem;color:#555;margin-bottom:.5rem"></i>
          <span style="font-size:.72rem;color:#555">${_esc(activeMeeting.name)}</span>
        </div>
      </div>
      <div class="mini-title">${_esc(activeMeeting.name)}</div>
      <div class="mini-controls">
        <button class="mini-btn btn-return" id="returnToMeeting">Return</button>
        <button class="mini-btn btn-quit"   id="quitMiniMeeting">Leave</button>
      </div>
    `;
    document.body.appendChild(widget);

    const miniVideo       = document.getElementById('miniVideo');
    const miniPlaceholder = document.getElementById('miniPlaceholder');
    let miniStream = null;

    if (activeMeeting.cam) {
      navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        .then(stream => {
          miniStream = stream;
          miniVideo.srcObject = stream;
          miniPlaceholder.style.display = 'none';
        })
        .catch(() => {});
    }

    document.getElementById('returnToMeeting').addEventListener('click', () => {
      if (miniStream) miniStream.getTracks().forEach(t => t.stop());
      window.location.href = `/room?id=${activeMeeting.id}&type=${activeMeeting.type}`;
    });

    document.getElementById('quitMiniMeeting').addEventListener('click', async () => {
      const fd = new FormData();
      fd.append('room_id',   activeMeeting.id);
      fd.append('room_type', activeMeeting.type);
      fd.append('student_id', studentId);
      await fetch('/rooms/leave', { method: 'POST', body: fd });
      sessionStorage.removeItem('active_meeting');
      widget.remove();
    });
  }
})();
