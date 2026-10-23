// Application Controller
const app = {
  state: {
    profile: null,
    tasks: [],
    analytics: null,
    activePlan: null,
    systemStatus: null,
    activeSection: 'dashboard'
  },

  init: async function() {
    this.setupEventListeners();
    this.setDefaultDates();
    await this.loadInitialData();
  },

  setDefaultDates: function() {
    const today = new Date().toISOString().split('T')[0];
    const planStartDate = document.getElementById('plan-start-date');
    if (planStartDate) planStartDate.value = today;
    const taskDeadline = document.getElementById('task-form-deadline');
    if (taskDeadline) taskDeadline.value = today;
  },

  setupEventListeners: function() {
    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
      item.addEventListener('click', (e) => {
        const targetSection = e.currentTarget.dataset.section;
        this.navigateTo(targetSection);
      });
    });

    // Mobile sidebar toggle
    const mobileToggle = document.getElementById('mobile-toggle');
    const sidebar = document.getElementById('sidebar');
    if (mobileToggle && sidebar) {
      mobileToggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
      });
    }

    // Refresh quote button
    const refreshQuoteBtn = document.getElementById('refresh-quote-btn');
    if (refreshQuoteBtn) {
      refreshQuoteBtn.addEventListener('click', () => this.loadQuote());
    }

    // Dashboard quick action buttons
    const dashPlanBtn = document.getElementById('dash-quick-plan-btn');
    if (dashPlanBtn) dashPlanBtn.addEventListener('click', () => this.navigateTo('planner'));

    const dashAllTasksBtn = document.getElementById('dash-view-all-tasks');
    if (dashAllTasksBtn) dashAllTasksBtn.addEventListener('click', () => this.navigateTo('tasks'));

    const dashOpenPlannerBtn = document.getElementById('dash-open-planner-btn');
    if (dashOpenPlannerBtn) dashOpenPlannerBtn.addEventListener('click', () => this.navigateTo('planner'));

    // Task Management Filter and Search
    const taskStatusFilter = document.getElementById('task-filter-status');
    const taskSubjectFilter = document.getElementById('task-filter-subject');
    const taskSearchInput = document.getElementById('task-search-input');

    if (taskStatusFilter) taskStatusFilter.addEventListener('change', () => this.loadTasks());
    if (taskSubjectFilter) taskSubjectFilter.addEventListener('change', () => this.loadTasks());
    if (taskSearchInput) {
      let debounceTimeout;
      taskSearchInput.addEventListener('input', () => {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => this.loadTasks(), 300);
      });
    }

    // Add Task Modal buttons
    const openAddTaskBtn = document.getElementById('open-add-task-modal-btn');
    const closeTaskModalBtn = document.getElementById('close-task-modal-btn');
    const cancelTaskModalBtn = document.getElementById('cancel-task-modal-btn');
    const taskForm = document.getElementById('task-form');

    if (openAddTaskBtn) openAddTaskBtn.addEventListener('click', () => this.openTaskModal());
    if (closeTaskModalBtn) closeTaskModalBtn.addEventListener('click', () => this.closeTaskModal());
    if (cancelTaskModalBtn) cancelTaskModalBtn.addEventListener('click', () => this.closeTaskModal());
    if (taskForm) taskForm.addEventListener('submit', (e) => this.handleTaskFormSubmit(e));

    // Profile Form
    const profileForm = document.getElementById('profile-form');
    if (profileForm) profileForm.addEventListener('submit', (e) => this.handleProfileSubmit(e));

    const addSubjectTagBtn = document.getElementById('add-subject-tag-btn');
    const newSubjectInput = document.getElementById('new-subject-input');
    if (addSubjectTagBtn && newSubjectInput) {
      addSubjectTagBtn.addEventListener('click', () => {
        const val = newSubjectInput.value.trim();
        if (val) {
          this.addProfileSubject(val);
          newSubjectInput.value = '';
        }
      });
      newSubjectInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          addSubjectTagBtn.click();
        }
      });
    }

    // Planner UI Controls
    const addSubjectRowBtn = document.getElementById('add-subject-row-btn');
    if (addSubjectRowBtn) {
      addSubjectRowBtn.addEventListener('click', () => this.addPlannerSubjectRow());
    }

    const planStartDateInput = document.getElementById('plan-start-date');
    if (planStartDateInput) {
      planStartDateInput.addEventListener('change', (e) => {
        const newStart = e.target.value;
        if (newStart) {
          document.querySelectorAll('.row-subj-exam').forEach(inp => {
            inp.min = newStart;
          });
        }
      });
    }

    const generatePlanBtn = document.getElementById('generate-plan-submit-btn');
    if (generatePlanBtn) {
      generatePlanBtn.addEventListener('click', () => this.handleGeneratePlan());
    }

    // Focus Music Controls
    const loadMusicBtn = document.getElementById('load-music-btn');
    if (loadMusicBtn) {
      loadMusicBtn.addEventListener('click', () => this.loadMusic());
    }

    // AI Assistant Drawer
    const openAssistantBtn = document.getElementById('open-assistant-btn');
    const closeAssistantBtn = document.getElementById('close-assistant-btn');
    const assistantModal = document.getElementById('assistant-modal');
    const assistantSendBtn = document.getElementById('assistant-send-btn');
    const assistantPromptInput = document.getElementById('assistant-prompt-input');

    if (openAssistantBtn && assistantModal) {
      openAssistantBtn.addEventListener('click', () => assistantModal.classList.add('active'));
    }
    if (closeAssistantBtn && assistantModal) {
      closeAssistantBtn.addEventListener('click', () => assistantModal.classList.remove('active'));
    }
    if (assistantSendBtn && assistantPromptInput) {
      assistantSendBtn.addEventListener('click', () => this.sendAssistantPrompt());
      assistantPromptInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          this.sendAssistantPrompt();
        }
      });
    }
  },

  navigateTo: function(sectionId) {
    this.state.activeSection = sectionId;

    // Update active nav item
    document.querySelectorAll('.nav-item').forEach(item => {
      item.classList.toggle('active', item.dataset.section === sectionId);
    });

    // Close mobile sidebar if open
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.classList.remove('open');

    // Switch view
    document.querySelectorAll('.section-view').forEach(view => {
      view.classList.toggle('active', view.id === `view-${sectionId}`);
    });

    // Refresh view specific data
    if (sectionId === 'dashboard') {
      this.loadDashboard();
    } else if (sectionId === 'tasks') {
      this.loadTasks();
    } else if (sectionId === 'tracker') {
      this.loadAnalytics();
    } else if (sectionId === 'planner') {
      this.loadActivePlan();
    } else if (sectionId === 'profile') {
      this.renderProfileForm();
    }
  },

  loadInitialData: async function() {
    try {
      await Promise.all([
        this.loadSystemStatus(),
        this.loadProfile(),
        this.loadQuote(),
        this.loadTasks(),
        this.loadAnalytics(),
        this.loadActivePlan()
      ]);
    } catch (err) {
      console.error('Initialization error:', err);
      this.showToast('Some initial data could not be loaded.', 'error');
    }
  },

  loadSystemStatus: async function() {
    try {
      const status = await API.getStatus();
      this.state.systemStatus = status;

      const statusPill = document.getElementById('system-status-pill');
      const statusText = document.getElementById('status-text');
      const assistantBadge = document.getElementById('assistant-model-badge');

      if (status.api_key_configured) {
        if (statusText) statusText.innerText = 'AI & Heuristic Online';
        if (assistantBadge) assistantBadge.innerText = `OpenRouter (${status.ai_model})`;
      } else {
        if (statusText) statusText.innerText = 'Rule-Based Engine Active';
        if (assistantBadge) assistantBadge.innerText = 'Local Study Coach (Rule-Based Fallback)';
      }
    } catch (e) {
      console.warn('System status check failed:', e);
    }
  },

  loadQuote: async function() {
    try {
      const res = await API.getQuote();
      const quoteText = document.getElementById('header-quote-text');
      if (quoteText && res.quote) {
        quoteText.innerText = res.quote;
      }
    } catch (e) {
      console.warn('Quote load failed:', e);
    }
  },

  loadProfile: async function() {
    try {
      const prof = await API.getProfile();
      this.state.profile = prof;

      // Update Header & Greetings
      const headerUsername = document.getElementById('header-username');
      const userAvatar = document.getElementById('user-avatar');
      const greeting = document.getElementById('dash-greeting');
      const subtext = document.getElementById('dash-subtext');

      if (headerUsername && prof.name) headerUsername.innerText = prof.name;
      if (userAvatar && prof.name) userAvatar.innerText = prof.name.charAt(0).toUpperCase();
      if (greeting && prof.name) greeting.innerText = `Welcome back, ${prof.name}! 👋`;
      if (subtext && prof.target_exam) {
        subtext.innerText = `Targeting: ${prof.target_exam} • Availability: ${prof.daily_study_hours} hrs/day`;
      }

      this.populateSubjectFilters(prof.subjects || []);
      this.populatePlannerSubjectsFromProfile(prof);
    } catch (e) {
      console.error('Failed to load profile:', e);
    }
  },

  populateSubjectFilters: function(subjects) {
    const filterSelect = document.getElementById('task-filter-subject');
    if (!filterSelect) return;

    const currentVal = filterSelect.value;
    filterSelect.innerHTML = '<option value="">All Subjects</option>';
    subjects.forEach(subj => {
      const opt = document.createElement('option');
      opt.value = subj;
      opt.innerText = subj;
      filterSelect.appendChild(opt);
    });
    filterSelect.value = currentVal;
  },

  loadTasks: async function() {
    try {
      const statusFilter = document.getElementById('task-filter-status')?.value || '';
      const subjectFilter = document.getElementById('task-filter-subject')?.value || '';
      const searchQuery = document.getElementById('task-search-input')?.value || '';

      const tasks = await API.getTasks({
        status: statusFilter,
        subject: subjectFilter,
        search: searchQuery
      });

      this.state.tasks = tasks;
      this.renderTasksList(tasks);
      this.renderDashboardTasks(tasks);
    } catch (e) {
      console.error('Failed to load tasks:', e);
    }
  },

  renderTasksList: function(tasks) {
    const container = document.getElementById('tasks-full-list');
    if (!container) return;

    if (!tasks || tasks.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📋</div>
          <h4>No tasks found</h4>
          <p>Create your first task or adjust your search filters.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = tasks.map(t => this.createTaskItemHtml(t)).join('');
  },

  renderDashboardTasks: function(tasks) {
    const container = document.getElementById('dash-tasks-container');
    if (!container) return;

    // Show top 4 pending tasks or urgent tasks
    const pendingTasks = tasks.filter(t => !t.completed);
    const displayTasks = pendingTasks.length > 0 ? pendingTasks.slice(0, 4) : tasks.slice(0, 4);

    if (displayTasks.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🎉</div>
          <h4>All tasks complete!</h4>
          <p>Great job! Use the Study Planner to schedule your next revision session.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = displayTasks.map(t => this.createTaskItemHtml(t)).join('');
  },

  createTaskItemHtml: function(t) {
    const todayStr = new Date().toISOString().split('T')[0];
    const isOverdue = !t.completed && t.deadline < todayStr;
    const isToday = !t.completed && t.deadline === todayStr;

    let deadlineBadge = `<span style="color: ${isOverdue ? 'var(--accent-rose)' : isToday ? 'var(--accent-amber)' : 'var(--text-secondary)'}; font-weight: 500;">
      📅 Due: ${t.deadline} ${isOverdue ? '(Overdue!)' : isToday ? '(Today)' : ''}
    </span>`;

    const priorityClass = `badge-${t.priority.toLowerCase()}`;

    return `
      <div class="task-item" id="task-card-${t.id}">
        <div class="task-left">
          <input type="checkbox" class="task-checkbox" ${t.completed ? 'checked' : ''} onchange="app.handleToggleTask(${t.id})">
          <div class="task-details">
            <div class="task-title ${t.completed ? 'completed' : ''}">${this.escapeHtml(t.title)}</div>
            <div class="task-meta">
              <span class="badge ${priorityClass}">${t.priority}</span>
              <span style="background: rgba(255,255,255,0.06); padding: 2px 6px; border-radius: 4px;">📚 ${this.escapeHtml(t.subject)}</span>
              <span>⏱️ ${t.duration_minutes}m</span>
              ${deadlineBadge}
            </div>
          </div>
        </div>
        <div class="task-actions">
          <button class="icon-btn" title="Edit Task" onclick="app.openEditTaskModal(${t.id})">✏️</button>
          <button class="icon-btn delete" title="Delete Task" onclick="app.handleDeleteTask(${t.id})">🗑️</button>
        </div>
      </div>
    `;
  },

  handleToggleTask: async function(taskId) {
    try {
      const res = await API.toggleTask(taskId);
      this.showToast(res.message, 'success');
      await this.loadTasks();
      await this.loadAnalytics();
    } catch (e) {
      console.error('Failed to toggle task:', e);
      this.showToast('Could not update task status', 'error');
    }
  },

  handleDeleteTask: async function(taskId) {
    if (!confirm('Are you sure you want to delete this task?')) return;
    try {
      await API.deleteTask(taskId);
      this.showToast('Task deleted successfully', 'info');
      await this.loadTasks();
      await this.loadAnalytics();
    } catch (e) {
      console.error('Failed to delete task:', e);
      this.showToast('Could not delete task', 'error');
    }
  },

  openTaskModal: function(task = null) {
    const modal = document.getElementById('task-modal');
    const titleElem = document.getElementById('task-modal-title');
    const idInput = document.getElementById('task-form-id');
    const titleInput = document.getElementById('task-form-title');
    const subjectInput = document.getElementById('task-form-subject');
    const priorityInput = document.getElementById('task-form-priority');
    const deadlineInput = document.getElementById('task-form-deadline');
    const durationInput = document.getElementById('task-form-duration');
    const notesInput = document.getElementById('task-form-notes');

    if (task) {
      titleElem.innerText = 'Edit Study Task';
      idInput.value = task.id;
      titleInput.value = task.title;
      subjectInput.value = task.subject;
      priorityInput.value = task.priority;
      deadlineInput.value = task.deadline;
      durationInput.value = task.duration_minutes;
      notesInput.value = task.notes || '';
    } else {
      titleElem.innerText = 'Add New Study Task';
      idInput.value = '';
      titleInput.value = '';
      subjectInput.value = this.state.profile?.subjects?.[0] || 'Mathematics';
      priorityInput.value = 'Medium';
      deadlineInput.value = new Date().toISOString().split('T')[0];
      durationInput.value = '60';
      notesInput.value = '';
    }

    modal.classList.add('active');
  },

  openEditTaskModal: function(taskId) {
    const task = this.state.tasks.find(t => t.id === taskId);
    if (task) {
      this.openTaskModal(task);
    }
  },

  closeTaskModal: function() {
    const modal = document.getElementById('task-modal');
    if (modal) modal.classList.remove('active');
  },

  handleTaskFormSubmit: async function(e) {
    e.preventDefault();
    const taskId = document.getElementById('task-form-id').value;
    const taskData = {
      title: document.getElementById('task-form-title').value.trim(),
      subject: document.getElementById('task-form-subject').value.trim(),
      priority: document.getElementById('task-form-priority').value,
      deadline: document.getElementById('task-form-deadline').value,
      duration_minutes: parseInt(document.getElementById('task-form-duration').value, 10) || 60,
      notes: document.getElementById('task-form-notes').value.trim()
    };

    if (!taskData.title || !taskData.subject || !taskData.deadline) {
      this.showToast('Please fill all required fields.', 'error');
      return;
    }

    try {
      if (taskId) {
        await API.updateTask(taskId, taskData);
        this.showToast('Task updated successfully!', 'success');
      } else {
        await API.createTask(taskData);
        this.showToast('New task added successfully!', 'success');
      }
      this.closeTaskModal();
      await this.loadTasks();
      await this.loadAnalytics();
    } catch (err) {
      console.error('Task save error:', err);
      this.showToast(err.message || 'Failed to save task', 'error');
    }
  },

  loadAnalytics: async function() {
    try {
      const data = await API.getAnalytics();
      this.state.analytics = data;

      // Dashboard KPI counts
      this.setElemText('kpi-total-tasks', data.total_tasks);
      this.setElemText('kpi-total-hours', `${data.total_study_hours} study hrs`);
      this.setElemText('kpi-completed-tasks', data.completed_tasks);
      this.setElemText('kpi-completion-rate', `${data.completion_rate}% finished`);
      this.setElemText('kpi-pending-tasks', data.pending_tasks);
      this.setElemText('kpi-urgent-tasks', data.today_tasks + data.overdue_tasks);
      this.setElemText('kpi-overdue-sub', `${data.overdue_tasks} overdue, ${data.today_tasks} today`);

      // Dashboard Progress Bar
      this.setElemText('dash-progress-label', `${data.completion_rate}%`);
      const dashBar = document.getElementById('dash-progress-bar');
      if (dashBar) dashBar.style.width = `${data.completion_rate}%`;

      // Tracker View KPIs
      this.setElemText('tracker-completion-rate', `${data.completion_rate}%`);
      this.setElemText('tracker-tasks-ratio', `${data.completed_tasks} of ${data.total_tasks} tasks`);
      this.setElemText('tracker-completed-hours', `${data.completed_study_hours} hrs`);
      this.setElemText('tracker-total-hours', `of ${data.total_study_hours} hrs total`);
      this.setElemText('tracker-pending-count', data.pending_tasks);
      this.setElemText('tracker-overdue-count', data.overdue_tasks);

      // Render Subject-wise breakdown
      this.renderSubjectBreakdown(data.subject_breakdown);

      // Render Priority breakdown
      this.renderPriorityBreakdown(data.priority_distribution, data.total_tasks);
    } catch (e) {
      console.error('Failed to load analytics:', e);
    }
  },

  renderSubjectBreakdown: function(breakdown) {
    const container = document.getElementById('tracker-subject-breakdown');
    if (!container) return;

    if (!breakdown || breakdown.length === 0) {
      container.innerHTML = '<div class="empty-state">No subject data recorded yet.</div>';
      return;
    }

    container.innerHTML = breakdown.map(s => `
      <div>
        <div style="display: flex; justify-content: space-between; font-size: 0.9rem; margin-bottom: 0.35rem;">
          <div>
            <strong>${this.escapeHtml(s.subject)}</strong>
            <span style="font-size: 0.75rem; color: var(--text-secondary); margin-left: 0.5rem;">
              (${s.completed}/${s.total} tasks • ${Math.round(s.total_minutes / 60 * 10)/10} hrs)
            </span>
          </div>
          <strong style="color: var(--accent-cyan);">${s.completion_rate}%</strong>
        </div>
        <div class="progress-container">
          <div class="progress-bar" style="width: ${s.completion_rate}%;"></div>
        </div>
      </div>
    `).join('');
  },

  renderPriorityBreakdown: function(distribution, total) {
    const container = document.getElementById('tracker-priority-breakdown');
    if (!container) return;

    const priorities = [
      { name: 'Urgent', count: distribution['Urgent'] || 0, color: 'var(--accent-rose)' },
      { name: 'High', count: distribution['High'] || 0, color: 'var(--accent-amber)' },
      { name: 'Medium', count: distribution['Medium'] || 0, color: 'var(--accent-primary)' },
      { name: 'Low', count: distribution['Low'] || 0, color: 'var(--text-secondary)' }
    ];

    container.innerHTML = priorities.map(p => {
      const pct = total > 0 ? Math.round((p.count / total) * 100) : 0;
      return `
        <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-color); padding: 0.75rem 1rem; border-radius: var(--radius-sm); display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="width: 10px; height: 10px; border-radius: 50%; background: ${p.color};"></span>
            <strong>${p.name} Priority</strong>
          </div>
          <div>
            <span>${p.count} tasks</span>
            <span style="color: var(--text-muted); font-size: 0.8rem; margin-left: 0.4rem;">(${pct}%)</span>
          </div>
        </div>
      `;
    }).join('');
  },

  // ----------------------------------------------------
  //  AI STUDY PLANNER LOGIC
  // ----------------------------------------------------
  populatePlannerSubjectsFromProfile: function(profile) {
    const container = document.getElementById('planner-subjects-container');
    if (!container) return;

    container.innerHTML = '';
    const subjects = profile?.subjects && profile.subjects.length > 0
      ? profile.subjects
      : ['Mathematics', 'Operating Systems', 'Data Structures'];

    const twoWeeksLater = new Date();
    twoWeeksLater.setDate(twoWeeksLater.getDate() + 14);
    const defaultExamDate = twoWeeksLater.toISOString().split('T')[0];

    subjects.forEach((subj, idx) => {
      this.addPlannerSubjectRow(subj, (idx % 3) + 3, defaultExamDate);
    });
  },

  addPlannerSubjectRow: function(name = '', difficulty = 3, examDate = '') {
    const container = document.getElementById('planner-subjects-container');
    if (!container) return;

    const currentStartDate = document.getElementById('plan-start-date')?.value || new Date().toISOString().split('T')[0];
    const rowId = `subj-row-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
    const row = document.createElement('div');
    row.className = 'planner-subject-row';
    row.id = rowId;
    row.style.display = 'grid';
    row.style.gridTemplateColumns = '2fr 1.5fr 1.5fr 3fr auto';
    row.style.gap = '0.75rem';
    row.style.alignItems = 'center';
    row.style.background = 'rgba(255,255,255,0.02)';
    row.style.padding = '0.5rem 0.75rem';
    row.style.borderRadius = 'var(--radius-sm)';
    row.style.border = '1px solid var(--border-color)';

    row.innerHTML = `
      <input type="text" class="input-control row-subj-name" placeholder="Subject Name" value="${this.escapeHtml(name)}" required>
      <select class="select-control row-subj-diff">
        <option value="1" ${difficulty == 1 ? 'selected' : ''}>1 - Very Easy</option>
        <option value="2" ${difficulty == 2 ? 'selected' : ''}>2 - Easy</option>
        <option value="3" ${difficulty == 3 ? 'selected' : ''}>3 - Moderate</option>
        <option value="4" ${difficulty == 4 ? 'selected' : ''}>4 - Difficult</option>
        <option value="5" ${difficulty == 5 ? 'selected' : ''}>5 - Very Hard</option>
      </select>
      <input type="date" class="input-control row-subj-exam" value="${examDate}" min="${currentStartDate}" title="Exam Date">
      <input type="text" class="input-control row-subj-topics" placeholder="Key topics (e.g. Recursion, Trees, Graphs)">
      <button type="button" class="icon-btn delete" onclick="document.getElementById('${rowId}').remove()" title="Remove Subject">✕</button>
    `;

    container.appendChild(row);
  },

  handleGeneratePlan: async function() {
    const rows = document.querySelectorAll('.planner-subject-row');
    const subjects = [];

    rows.forEach((r, idx) => {
      const name = r.querySelector('.row-subj-name')?.value.trim();
      const difficulty = parseInt(r.querySelector('.row-subj-diff')?.value, 10) || 3;
      const exam_date = r.querySelector('.row-subj-exam')?.value || null;
      const topics = r.querySelector('.row-subj-topics')?.value.trim() || '';

      if (name) {
        subjects.push({ name, difficulty, exam_date, topics });
      }
    });

    if (subjects.length === 0) {
      this.showToast('Please specify at least one subject.', 'error');
      this.renderPlanError('Please enter at least one subject name before generating a study timetable.');
      return;
    }

    const dailyHours = parseFloat(document.getElementById('plan-daily-hours')?.value) || 4.0;
    const daysCount = parseInt(document.getElementById('plan-days-count')?.value, 10) || 7;
    const startDate = document.getElementById('plan-start-date')?.value || new Date().toISOString().split('T')[0];
    const modeSelect = document.getElementById('planner-mode-select')?.value;
    const forceRuleBased = (modeSelect === 'rule');

    // Client-side pre-validation: check exam dates against start date
    for (let i = 0; i < subjects.length; i++) {
      const s = subjects[i];
      if (s.exam_date && startDate && s.exam_date < startDate) {
        let formattedStart = startDate;
        let formattedExam = s.exam_date;
        if (startDate.includes('-')) {
          const parts = startDate.split('-');
          if (parts[0].length === 4) formattedStart = `${parts[2]}-${parts[1]}-${parts[0]}`;
        }
        if (s.exam_date.includes('-')) {
          const parts = s.exam_date.split('-');
          if (parts[0].length === 4) formattedExam = `${parts[2]}-${parts[1]}-${parts[0]}`;
        }
        const errorMsg = `Invalid exam date for '${s.name}': Exam date (${formattedExam}) is earlier than the schedule start date (${formattedStart}). Please choose an exam date on or after the start date.`;
        this.showToast(errorMsg, 'error');
        this.renderPlanError(errorMsg);
        return;
      }
    }

    const submitBtn = document.getElementById('generate-plan-submit-btn');
    const origHtml = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span>⏳</span> Computing Balanced Timetable...';
    submitBtn.disabled = true;

    try {
      const payload = {
        subjects,
        daily_hours: dailyHours,
        days_count: daysCount,
        start_date: startDate,
        force_rule_based: forceRuleBased
      };

      const planResult = await API.generatePlan(payload);
      this.state.activePlan = planResult;
      this.renderPlanOutput(planResult);
      this.updateDashboardPlanPreview(planResult);
      this.showToast(`Study Timetable generated via ${planResult.generated_by}!`, 'success');
    } catch (err) {
      console.error('Plan generation error:', err);
      const friendlyMsg = err.message || 'Failed to generate timetable. Please check your inputs.';
      this.showToast(friendlyMsg, 'error');
      this.renderPlanError(friendlyMsg);
    } finally {
      submitBtn.innerHTML = origHtml;
      submitBtn.disabled = false;
    }
  },

  renderPlanError: function(message) {
    const outputArea = document.getElementById('planner-output-area');
    if (!outputArea) return;
    outputArea.innerHTML = `
      <div style="background: rgba(244, 63, 94, 0.12); border: 1px solid var(--accent-rose); border-radius: var(--radius-md); padding: 1.25rem 1.5rem; margin-top: 1rem; color: #fecdd3; animation: fadeIn 0.2s ease-out;">
        <div style="display: flex; align-items: center; gap: 0.6rem; font-weight: 700; font-size: 1.05rem; margin-bottom: 0.5rem; color: #fda4af;">
          <span>⚠️</span> Timetable Generation Error
        </div>
        <p style="font-size: 0.9rem; line-height: 1.5; color: #ffe4e6;">
          ${this.escapeHtml(message)}
        </p>
        <div style="margin-top: 0.75rem; font-size: 0.8rem; color: var(--text-secondary); border-top: 1px solid rgba(244,63,94,0.2); padding-top: 0.5rem;">
          💡 <em>Tip: Verify that all exam dates occur on or after the schedule start date, each subject has a name, and study hours are greater than 0.</em>
        </div>
      </div>
    `;
  },

  loadActivePlan: async function() {
    try {
      const plan = await API.getActivePlan();
      if (plan) {
        const fullPlan = plan.schedule_data || plan;
        this.state.activePlan = fullPlan;
        this.renderPlanOutput(fullPlan);
        this.updateDashboardPlanPreview(fullPlan);
      }
    } catch (e) {
      console.warn('Failed to load active plan:', e);
    }
  },

  updateDashboardPlanPreview: function(plan) {
    const summaryElem = document.getElementById('dash-plan-summary');
    const badgeElem = document.getElementById('dash-plan-badge');

    if (badgeElem) {
      const isAI = plan.is_ai;
      badgeElem.className = isAI ? 'badge badge-ai' : 'badge badge-rule';
      badgeElem.innerText = isAI ? `AI: ${plan.model_used || 'OpenRouter'}` : 'Rule-Based Heuristic';
    }

    if (summaryElem && plan.summary) {
      summaryElem.innerText = plan.summary;
    }
  },

  renderPlanOutput: function(plan) {
    const outputArea = document.getElementById('planner-output-area');
    if (!outputArea) return;

    const isAI = plan.is_ai;
    const badgeClass = isAI ? 'badge-ai' : 'badge-rule';
    const badgeLabel = isAI ? `🤖 ${plan.generated_by} (${plan.model_used})` : `⚙️ ${plan.generated_by} (Priority-Weighted)`;

    let fallbackNotice = '';
    if (plan.fallback_triggered || plan.ai_status?.includes('Switched to Rule-Based')) {
      fallbackNotice = `
        <div style="background: rgba(245, 158, 11, 0.15); border: 1px solid var(--accent-amber); border-radius: var(--radius-sm); padding: 0.75rem 1rem; margin-bottom: 1rem; font-size: 0.85rem; color: #fde68a;">
          🔔 <strong>Notice:</strong> ${this.escapeHtml(plan.ai_status)}
        </div>
      `;
    }

    const weightsHtml = plan.subject_weights && plan.subject_weights.length > 0 ? `
      <div class="card" style="margin-bottom: 1.5rem;">
        <h4 style="font-size: 0.95rem; font-weight: 600; margin-bottom: 0.75rem;">Subject Priority & Time Allocation Breakdown</h4>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem;">
          ${plan.subject_weights.map(sw => `
            <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 0.75rem;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                <strong>${this.escapeHtml(sw.name)}</strong>
                <span class="badge ${sw.difficulty >= 4 ? 'badge-urgent' : sw.difficulty == 3 ? 'badge-high' : 'badge-medium'}">Diff: ${sw.difficulty}/5</span>
              </div>
              <div style="font-size: 0.8rem; color: var(--accent-cyan); font-weight: 600;">
                ⏱️ Target: ${sw.target_hours_per_day} hrs/day
              </div>
              ${sw.urgency_label ? `<div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.2rem;">${sw.urgency_label}</div>` : ''}
            </div>
          `).join('')}
        </div>
      </div>
    ` : '';

    const daysHtml = plan.daily_schedule && plan.daily_schedule.length > 0 ? `
      <div class="timetable-days-grid">
        ${plan.daily_schedule.map(d => `
          <div class="day-card">
            <div class="day-card-header">
              <h4>${d.day_name} • ${d.date}</h4>
              <span>${d.total_hours} hrs</span>
            </div>
            <div class="day-sessions">
              ${d.sessions.map(s => {
                const diffClass = s.difficulty >= 4 ? 'hard' : s.difficulty == 3 ? 'medium' : 'easy';
                return `
                  <div class="session-box ${diffClass}">
                    <div class="session-top">
                      <span class="session-subject">${this.escapeHtml(s.subject)}</span>
                      <span class="session-time">Session ${s.session_number} • ${s.duration_hours}h (${s.duration_minutes}m)</span>
                    </div>
                    <div class="session-topic">🎯 Focus: ${this.escapeHtml(s.topic || s.phase || 'Concept Review')}</div>
                    <div class="session-technique">💡 ${this.escapeHtml(s.technique || 'Pomodoro 50/10')}</div>
                    ${s.break_after_minutes ? `<div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 0.2rem;">☕ Followed by ${s.break_after_minutes} min rest</div>` : ''}
                  </div>
                `;
              }).join('')}
            </div>
          </div>
        `).join('')}
      </div>
    ` : '<div class="empty-state">No daily schedule generated.</div>';

    outputArea.innerHTML = `
      ${fallbackNotice}
      <div class="timetable-banner">
        <div>
          <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
            <h3 style="font-size: 1.15rem; font-weight: 700;">Active Timetable</h3>
            <span class="badge ${badgeClass}">${badgeLabel}</span>
          </div>
          <p style="font-size: 0.9rem; color: var(--text-secondary); max-width: 850px; line-height: 1.5;">
            ${this.escapeHtml(plan.summary || '')}
          </p>
        </div>
        <button class="btn btn-secondary btn-sm" onclick="window.print()">🖨️ Print / Save</button>
      </div>

      ${weightsHtml}
      ${daysHtml}
    `;
  },

  // ----------------------------------------------------
  //  STUDENT PROFILE LOGIC
  // ----------------------------------------------------
  renderProfileForm: function() {
    const prof = this.state.profile;
    if (!prof) return;

    this.setInputValue('prof-name', prof.name);
    this.setInputValue('prof-email', prof.email);
    this.setInputValue('prof-institution', prof.institution);
    this.setInputValue('prof-target-exam', prof.target_exam);
    this.setInputValue('prof-daily-hours', prof.daily_study_hours);
    this.setInputValue('prof-study-time', prof.preferred_study_time || 'Evening');

    this.renderProfileSubjectTags(prof.subjects || []);
  },

  renderProfileSubjectTags: function(subjects) {
    const container = document.getElementById('profile-subject-tags');
    if (!container) return;

    container.innerHTML = subjects.map(subj => `
      <div style="display: inline-flex; align-items: center; gap: 0.4rem; background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); color: #c7d2fe; padding: 0.3rem 0.75rem; border-radius: 9999px; font-size: 0.825rem;">
        <span>${this.escapeHtml(subj)}</span>
        <button type="button" style="background: none; border: none; color: inherit; cursor: pointer; font-size: 0.9rem;" onclick="app.removeProfileSubject('${this.escapeHtml(subj)}')">✕</button>
      </div>
    `).join('');
  },

  addProfileSubject: function(subject) {
    if (!this.state.profile) this.state.profile = {};
    if (!this.state.profile.subjects) this.state.profile.subjects = [];
    if (!this.state.profile.subjects.includes(subject)) {
      this.state.profile.subjects.push(subject);
      this.renderProfileSubjectTags(this.state.profile.subjects);
      this.populateSubjectFilters(this.state.profile.subjects);
    }
  },

  removeProfileSubject: function(subject) {
    if (!this.state.profile || !this.state.profile.subjects) return;
    this.state.profile.subjects = this.state.profile.subjects.filter(s => s !== subject);
    this.renderProfileSubjectTags(this.state.profile.subjects);
    this.populateSubjectFilters(this.state.profile.subjects);
  },

  handleProfileSubmit: async function(e) {
    e.preventDefault();
    const payload = {
      name: document.getElementById('prof-name')?.value.trim() || 'Student',
      email: document.getElementById('prof-email')?.value.trim() || '',
      institution: document.getElementById('prof-institution')?.value.trim() || '',
      target_exam: document.getElementById('prof-target-exam')?.value.trim() || '',
      daily_study_hours: parseFloat(document.getElementById('prof-daily-hours')?.value) || 4.0,
      preferred_study_time: document.getElementById('prof-study-time')?.value || 'Evening',
      subjects: this.state.profile?.subjects || []
    };

    try {
      const res = await API.updateProfile(payload);
      this.state.profile = res.profile;
      this.showToast('Student profile updated successfully!', 'success');
      await this.loadProfile();
    } catch (err) {
      console.error('Failed to update profile:', err);
      this.showToast('Could not save profile changes', 'error');
    }
  },

  // ----------------------------------------------------
  //  FOCUS MUSIC & AMBIENT AUDIO
  // ----------------------------------------------------
  loadMusic: async function() {
    const mood = document.getElementById('music-mood')?.value || 'focused';
    const lang = document.getElementById('music-lang')?.value || 'english';
    const ptype = document.getElementById('music-ptype')?.value || 'lofi';

    try {
      const res = await API.getMusicSuggest(mood, lang, ptype);
      this.updateMusicPlayer(res);
      this.showToast(`Loaded ${res.playlist_name}`, 'info');
    } catch (e) {
      console.error('Failed to load music playlist:', e);
      this.showToast('Could not load playlist', 'error');
    }
  },

  quickMusic: async function(mood, ptype) {
    this.navigateTo('music');
    const moodSelect = document.getElementById('music-mood');
    const ptypeSelect = document.getElementById('music-ptype');
    if (moodSelect) moodSelect.value = mood;
    if (ptypeSelect) ptypeSelect.value = ptype;
    await this.loadMusic();
  },

  updateMusicPlayer: function(data) {
    this.setElemText('current-playlist-title', data.playlist_name);
    this.setElemText('current-playlist-desc', data.description);

    const youtubeIframe = document.getElementById('youtube-iframe');
    const spotifyIframe = document.getElementById('spotify-iframe');
    const spotifyLink = document.getElementById('spotify-external-link');
    const youtubeLink = document.getElementById('youtube-external-link');

    if (youtubeIframe && data.youtube_url) youtubeIframe.src = data.youtube_url;
    if (spotifyIframe && data.spotify_embed) spotifyIframe.src = data.spotify_embed;
    if (spotifyLink && data.spotify_url) spotifyLink.href = data.spotify_url;
    if (youtubeLink && data.youtube_url) youtubeLink.href = data.youtube_url;
  },

  // ----------------------------------------------------
  //  AI STUDY ASSISTANT CHAT
  // ----------------------------------------------------
  setAssistantPrompt: function(text) {
    const input = document.getElementById('assistant-prompt-input');
    if (input) {
      input.value = text;
      this.sendAssistantPrompt();
    }
  },

  sendAssistantPrompt: async function() {
    const input = document.getElementById('assistant-prompt-input');
    const prompt = input?.value.trim();
    if (!prompt) return;

    const chatLog = document.getElementById('assistant-chat-log');
    if (!chatLog) return;

    // Append User Message
    chatLog.innerHTML += `
      <div style="background: rgba(99, 102, 241, 0.2); border: 1px solid rgba(99, 102, 241, 0.3); padding: 0.6rem 0.85rem; border-radius: var(--radius-sm); font-size: 0.875rem; align-self: flex-end; max-width: 85%;">
        🧑 <strong>You:</strong> ${this.escapeHtml(prompt)}
      </div>
    `;
    input.value = '';
    chatLog.scrollTop = chatLog.scrollHeight;

    // Temporary loading indicator
    const loadingId = `msg-loading-${Date.now()}`;
    chatLog.innerHTML += `
      <div id="${loadingId}" style="background: rgba(255, 255, 255, 0.05); padding: 0.6rem 0.85rem; border-radius: var(--radius-sm); font-size: 0.85rem; color: var(--text-secondary);">
        🤖 Thinking...
      </div>
    `;
    chatLog.scrollTop = chatLog.scrollHeight;

    try {
      const res = await API.askAssistant(prompt);
      document.getElementById(loadingId)?.remove();

      const modelBadge = res.model_used ? `<span style="font-size: 0.7rem; color: var(--accent-cyan); display: block; margin-top: 0.3rem;">Model: ${res.model_used}</span>` : '';
      chatLog.innerHTML += `
        <div style="background: rgba(255, 255, 255, 0.05); border: 1px solid var(--border-color); padding: 0.75rem 1rem; border-radius: var(--radius-sm); font-size: 0.875rem; line-height: 1.5; white-space: pre-wrap;">
          🤖 <strong>Study Coach:</strong>\n${this.escapeHtml(res.text)}
          ${modelBadge}
        </div>
      `;
      chatLog.scrollTop = chatLog.scrollHeight;
    } catch (err) {
      document.getElementById(loadingId)?.remove();
      chatLog.innerHTML += `
        <div style="background: rgba(244, 63, 94, 0.15); border: 1px solid var(--accent-rose); padding: 0.6rem 0.85rem; border-radius: var(--radius-sm); font-size: 0.85rem; color: #fda4af;">
          ⚠️ ${this.escapeHtml(err.message || 'Error communicating with assistant')}
        </div>
      `;
      chatLog.scrollTop = chatLog.scrollHeight;
    }
  },

  // ----------------------------------------------------
  //  UI UTILITIES
  // ----------------------------------------------------
  setElemText: function(id, text) {
    const elem = document.getElementById(id);
    if (elem) elem.innerText = text;
  },

  setInputValue: function(id, val) {
    const input = document.getElementById(id);
    if (input && val !== undefined && val !== null) input.value = val;
  },

  showToast: function(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
    toast.innerHTML = `<span>${icon}</span> <span>${this.escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  },

  escapeHtml: function(text) {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
};

// Initialize Application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  app.init();
});
