<script setup>
import { computed, onMounted, ref, watch } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE || 'https://exchange-book.onrender.com/api'

const isLoggedIn = ref(false)
const activeTab = ref('library')
const loginNickname = ref('')
const loginPassword = ref('')
const currentUser = ref(null)

const users = ref([])
const books = ref([])
const selectedBookId = ref(null)
const pageFilter = ref('')
const underlineInput = ref('')
const underlineInitialCommentInput = ref('')
const underlines = ref([])
const commentsByUnderline = ref({})
const commentDraftByUnderline = ref({})
const errorMessage = ref('')
const loading = ref(false)
const initializing = ref(false)
const loadingBooks = ref(false)
const loadingUnderlines = ref(false)
const loadingAdminAction = ref(false)
const loadingReadingBoard = ref(false)
const coldStartMessage = ref('')
const adminUserNickname = ref('')
const adminUserPassword = ref('')
const adminBookTitle = ref('')
const adminBookAuthor = ref('')
const adminBookTotalPages = ref('')
const adminMessage = ref('')
const readingBoard = ref([])
const readingDraftByUser = ref({})
const readingMessage = ref('')

const selectedBook = computed(() =>
  books.value.find((book) => book.id === selectedBookId.value) ?? null,
)

const usersById = computed(() => {
  const mapped = {}
  for (const user of users.value) {
    mapped[user.id] = user
  }
  return mapped
})

const readingStatusOptions = [
  { value: 'before', label: '읽기전' },
  { value: 'reading', label: '읽는중' },
  { value: 'done', label: '완료' },
]

function getReadingProgressPercent(item) {
  const totalPages = item?.current_book?.total_pages
  const currentPage = item?.user?.current_page
  const status = item?.user?.reading_status

  if (status === 'done' && totalPages && totalPages > 0) {
    return 100
  }

  if (!totalPages || totalPages <= 0 || currentPage == null || currentPage < 0) {
    return null
  }
  const safeCurrent = Math.min(currentPage, totalPages)
  return Math.round((safeCurrent / totalPages) * 100)
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function request(path, options = {}, retryCount = 2, timeoutMs = 20000) {
  let lastError

  for (let attempt = 0; attempt <= retryCount; attempt += 1) {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)

    try {
      const response = await fetch(`${API_BASE}${path}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
        signal: controller.signal,
      })
      clearTimeout(timer)

      if (!response.ok) {
        throw new Error(`요청 실패: ${response.status}`)
      }
      if (response.status === 204) return null
      return response.json()
    } catch (error) {
      clearTimeout(timer)
      lastError = error
      if (attempt < retryCount) {
        await delay(1200 * (attempt + 1))
      }
    }
  }

  throw lastError
}

async function warmUpBackend() {
  coldStartMessage.value = '서버를 깨우는 중입니다. 첫 요청은 최대 50초 이상 걸릴 수 있어요...'
  await request('/health', { method: 'GET' }, 3, 70000)
  coldStartMessage.value = ''
}

async function loadUsers() {
  users.value = await request('/users')
}

function syncReadingDrafts(items) {
  const next = {}
  for (const item of items) {
    next[item.user.id] = {
      current_book_id: item.user.current_book_id ?? '',
      reading_status: item.user.reading_status ?? 'before',
      current_page: item.user.current_page ?? '',
    }
  }
  readingDraftByUser.value = next
}

async function loadReadingBoard() {
  loadingReadingBoard.value = true
  try {
    readingBoard.value = await request('/dashboards/board')
    syncReadingDrafts(readingBoard.value)
  } finally {
    loadingReadingBoard.value = false
  }
}

function syncCurrentPageForDone(userId) {
  const draft = readingDraftByUser.value[userId]
  if (!draft || draft.reading_status !== 'done') return

  const selectedBookId = draft.current_book_id === '' ? null : Number(draft.current_book_id)
  if (selectedBookId === null || Number.isNaN(selectedBookId)) return

  const selectedBook = books.value.find((book) => book.id === selectedBookId)
  if (selectedBook?.total_pages && selectedBook.total_pages > 0) {
    draft.current_page = selectedBook.total_pages
  }
}

async function ensureDisplayBooks() {
  loadingBooks.value = true
  try {
    const currentBooks = await request('/books')
    if (currentBooks.length === 0) {
      const defaults = [
        { title: '아몬드', author: '손원평' },
        { title: '달러구트 꿈 백화점', author: '이미예' },
        { title: '불편한 편의점', author: '김호연' },
      ]
      for (const item of defaults) {
        await request('/books', {
          method: 'POST',
          body: JSON.stringify(item),
        })
      }
      books.value = await request('/books')
    } else {
      books.value = currentBooks
    }

    if (!selectedBookId.value && books.value.length > 0) {
      selectedBookId.value = books.value[0].id
    }
  } finally {
    loadingBooks.value = false
  }
}

async function loadUnderlines() {
  loadingUnderlines.value = true
  if (!selectedBookId.value) {
    underlines.value = []
    commentsByUnderline.value = {}
    loadingUnderlines.value = false
    return
  }
  try {
    const query = pageFilter.value ? `?page=${pageFilter.value}` : ''
    underlines.value = await request(`/underlines/book/${selectedBookId.value}${query}`)
    await loadCommentsForUnderlines(underlines.value)
  } finally {
    loadingUnderlines.value = false
  }
}

async function loadCommentsForUnderlines(lines) {
  if (!lines.length) {
    commentsByUnderline.value = {}
    return
  }

  const pairs = await Promise.all(
    lines.map(async (line) => {
      const comments = await request(`/comments/underline/${line.id}`)
      return [line.id, comments]
    }),
  )

  commentsByUnderline.value = Object.fromEntries(pairs)
}

async function handleLogin() {
  if (!loginNickname.value.trim() || !loginPassword.value.trim()) return
  try {
    loading.value = true
    errorMessage.value = ''
    currentUser.value = await request('/users/login', {
      method: 'POST',
      body: JSON.stringify({
        nickname: loginNickname.value.trim(),
        password: loginPassword.value,
      }),
    })

    isLoggedIn.value = true
    loginPassword.value = ''
    await loadUsers()
    await ensureDisplayBooks()
    await loadUnderlines()
    await loadReadingBoard()
  } catch (error) {
    errorMessage.value = '로그인에 실패했습니다. 등록된 계정과 비밀번호를 확인해주세요.'
  } finally {
    loading.value = false
  }
}

async function handleSignup() {
  if (!loginNickname.value.trim() || !loginPassword.value.trim()) return
  try {
    loading.value = true
    errorMessage.value = ''
    await request('/users/signup', {
      method: 'POST',
      body: JSON.stringify({
        nickname: loginNickname.value.trim(),
        password: loginPassword.value,
      }),
    })
    errorMessage.value = '회원가입 완료. 이제 로그인해주세요.'
    await loadUsers()
  } catch {
    errorMessage.value = '회원가입에 실패했습니다. 이미 존재하는 닉네임인지 확인해주세요.'
  } finally {
    loading.value = false
  }
}

async function handleAddUnderline() {
  if (!currentUser.value || !selectedBookId.value || !underlineInput.value.trim()) return
  const pageNumber = Number(pageFilter.value || 1)
  if (Number.isNaN(pageNumber) || pageNumber < 1) return

  await request('/underlines', {
    method: 'POST',
    body: JSON.stringify({
      book_id: selectedBookId.value,
      user_id: currentUser.value.id,
      page: pageNumber,
      content: underlineInput.value.trim(),
      is_public: true,
      initial_comment: underlineInitialCommentInput.value.trim() || null,
    }),
  })

  underlineInput.value = ''
  underlineInitialCommentInput.value = ''
  await loadUnderlines()
}

async function handleDeleteUnderline(underlineId) {
  await request(`/underlines/${underlineId}`, {
    method: 'DELETE',
  })
  await loadUnderlines()
}

async function handleAddComment(underlineId) {
  const content = (commentDraftByUnderline.value[underlineId] ?? '').trim()
  if (!currentUser.value || !content) return

  await request('/comments', {
    method: 'POST',
    body: JSON.stringify({
      underline_id: underlineId,
      user_id: currentUser.value.id,
      content,
    }),
  })

  commentDraftByUnderline.value = {
    ...commentDraftByUnderline.value,
    [underlineId]: '',
  }

  const comments = await request(`/comments/underline/${underlineId}`)
  commentsByUnderline.value = {
    ...commentsByUnderline.value,
    [underlineId]: comments,
  }
}

async function handleDeleteComment(underlineId, commentId) {
  await request(`/comments/${commentId}`, {
    method: 'DELETE',
  })

  const comments = await request(`/comments/underline/${underlineId}`)
  commentsByUnderline.value = {
    ...commentsByUnderline.value,
    [underlineId]: comments,
  }
}

async function handleCreateUserByAdmin() {
  const nickname = adminUserNickname.value.trim()
  const password = adminUserPassword.value.trim()
  if (!nickname || !password) return

  loadingAdminAction.value = true
  try {
    await request('/users', {
      method: 'POST',
      body: JSON.stringify({ nickname, password }),
    })

    adminUserNickname.value = ''
    adminUserPassword.value = ''
    await loadUsers()
    adminMessage.value = '회원이 추가되었습니다.'
  } finally {
    loadingAdminAction.value = false
  }
}

async function handleCreateBookByAdmin() {
  const title = adminBookTitle.value.trim()
  const author = adminBookAuthor.value.trim()
  const totalPages = adminBookTotalPages.value === '' ? null : Number(adminBookTotalPages.value)
  if (!title || !author) return
  if (totalPages !== null && (Number.isNaN(totalPages) || totalPages < 1)) return

  loadingAdminAction.value = true
  try {
    await request('/books', {
      method: 'POST',
      body: JSON.stringify({ title, author, total_pages: totalPages }),
    })

    adminBookTitle.value = ''
    adminBookAuthor.value = ''
    adminBookTotalPages.value = ''
    await ensureDisplayBooks()
    await loadReadingBoard()
    adminMessage.value = '책이 추가되었습니다.'
  } finally {
    loadingAdminAction.value = false
  }
}

async function handleDeleteBookByAdmin(bookId) {
  loadingAdminAction.value = true
  try {
    await request(`/books/${bookId}`, {
      method: 'DELETE',
    })

    await ensureDisplayBooks()

    if (selectedBookId.value === bookId) {
      selectedBookId.value = books.value.length ? books.value[0].id : null
      await loadUnderlines()
    }

    await loadReadingBoard()

    adminMessage.value = '책이 삭제되었습니다.'
  } finally {
    loadingAdminAction.value = false
  }
}

async function handleSaveReadingCard(userId) {
  if (!currentUser.value || currentUser.value.id !== userId) return
  const draft = readingDraftByUser.value[userId]
  if (!draft) return

  const currentBookId = draft.current_book_id === '' ? null : Number(draft.current_book_id)
  let currentPage = draft.current_page === '' ? null : Number(draft.current_page)

  if (currentBookId !== null && Number.isNaN(currentBookId)) return
  if (currentPage !== null && (Number.isNaN(currentPage) || currentPage < 0)) return

  if (draft.reading_status === 'done') {
    const selectedBook = books.value.find((book) => book.id === currentBookId)
    if (selectedBook?.total_pages && selectedBook.total_pages > 0) {
      currentPage = selectedBook.total_pages
    }
  }

  loadingReadingBoard.value = true
  readingMessage.value = ''
  try {
    const updated = await request(`/users/${userId}/dashboard`, {
      method: 'PATCH',
      body: JSON.stringify({
        current_book_id: currentBookId,
        current_page: currentPage,
        reading_status: draft.reading_status,
      }),
    })

    if (currentUser.value?.id === updated.id) {
      currentUser.value = updated
    }

    await Promise.all([loadUsers(), loadReadingBoard()])
    readingMessage.value = '읽기 현황이 저장되었습니다.'
  } finally {
    loadingReadingBoard.value = false
  }
}

function handleLogout() {
  isLoggedIn.value = false
  activeTab.value = 'library'
  currentUser.value = null
  loginNickname.value = ''
  loginPassword.value = ''
  underlines.value = []
  commentsByUnderline.value = {}
  readingBoard.value = []
  readingDraftByUser.value = {}
  readingMessage.value = ''
}

watch(selectedBookId, async () => {
  if (isLoggedIn.value) {
    await loadUnderlines()
  }
})

onMounted(async () => {
  try {
    initializing.value = true
    await warmUpBackend()
    await loadUsers()
    await ensureDisplayBooks()
    await loadReadingBoard()
  } catch {
    errorMessage.value = '초기 데이터 로딩에 실패했습니다.'
  } finally {
    initializing.value = false
  }
})
</script>

<template>
  <main class="container">
    <section v-if="!isLoggedIn" class="login-card">
      <div v-if="initializing || coldStartMessage" class="initial-loader-wrap">
        <div class="spinner" aria-hidden="true"></div>
        <p class="meta-message">{{ coldStartMessage || '초기 데이터를 불러오는 중...' }}</p>
      </div>
      <template v-else>
        <h1>meet-zool</h1>
        <p>교환독서 서재에 입장하려면 닉네임으로 로그인하세요.</p>
        <div class="login-row">
          <div class="login-inputs">
            <input v-model="loginNickname" type="text" placeholder="닉네임 입력" @keyup.enter="handleLogin" />
            <input v-model="loginPassword" type="password" placeholder="비밀번호" @keyup.enter="handleLogin" />
          </div>
          <div class="login-actions">
            <button :disabled="loading" @click="handleLogin">로그인</button>
            <button :disabled="loading" @click="handleSignup">회원가입</button>
          </div>
        </div>
      </template>
      <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
    </section>

    <section v-else class="library-page">
      <header class="library-header">
        <div>
          <h1>{{ currentUser?.nickname }}님의 서재</h1>
          <p>책을 고르고, 페이지 번호와 밑줄 내용을 작성해보세요.</p>
        </div>
        <button @click="handleLogout">로그아웃</button>
      </header>

      <div class="tab-row">
        <button :class="['tab-btn', { active: activeTab === 'library' }]" @click="activeTab = 'library'">서재</button>
        <button :class="['tab-btn', { active: activeTab === 'reading' }]" @click="activeTab = 'reading'">읽기 현황</button>
        <button
          v-if="currentUser?.is_admin"
          :class="['tab-btn', { active: activeTab === 'admin' }]"
          @click="activeTab = 'admin'"
        >
          Admin
        </button>
      </div>

      <section v-if="activeTab === 'library'" class="bookshelf">
        <template v-if="loadingBooks">
          <article v-for="n in 6" :key="`book-skeleton-${n}`" class="book-card skeleton-card">
            <div class="book-cover skeleton-block"></div>
            <div class="skeleton-line"></div>
            <div class="skeleton-line short"></div>
          </article>
        </template>
        <template v-else>
          <article
            v-for="book in books"
            :key="book.id"
            class="book-card"
            :class="{ selected: selectedBookId === book.id }"
            @click="selectedBookId = book.id"
          >
            <div class="book-cover">📚</div>
            <strong>{{ book.title }}</strong>
            <span>{{ book.author }}</span>
          </article>
        </template>
      </section>

      <section v-if="activeTab === 'library' && selectedBook" class="editor-panel">
        <h2>{{ selectedBook.title }}</h2>

        <div class="action-row page-query-row">
          <input v-model="pageFilter" type="number" min="1" placeholder="페이지 번호" />
          <button :disabled="loadingUnderlines" @click="loadUnderlines">페이지 조회</button>
        </div>

        <div class="action-row underline-content-row">
          <input v-model="underlineInput" type="text" placeholder="밑줄 내용을 입력하세요" @keyup.enter="handleAddUnderline" />
        </div>

        <div class="action-row underline-comment-row">
          <input
            v-model="underlineInitialCommentInput"
            type="text"
            placeholder="첫 코멘트(선택)"
            @keyup.enter="handleAddUnderline"
          />
          <button :disabled="loadingUnderlines" @click="handleAddUnderline">밑줄 저장</button>
        </div>

        <div class="underline-list">
          <div v-if="loadingUnderlines" class="underline-carousel-loader" aria-busy="true">
            <div class="carousel-track">
              <article v-for="n in 4" :key="`underline-skeleton-${n}`" class="carousel-card">
                <div class="skeleton-line short"></div>
                <div class="skeleton-line"></div>
                <div class="skeleton-line"></div>
                <div class="skeleton-line short"></div>
                <div class="skeleton-line"></div>
              </article>
            </div>
          </div>
          <template v-else>
            <article v-for="line in underlines" :key="line.id" class="underline-item">
              <div class="underline-header-row">
                <p class="meta">페이지 {{ line.page }}</p>
                <button
                  v-if="currentUser?.id === line.user_id"
                  class="delete-btn"
                  :disabled="loadingUnderlines"
                  @click="handleDeleteUnderline(line.id)"
                >
                  밑줄 삭제
                </button>
              </div>
              <p class="author">작성자: {{ usersById[line.user_id]?.nickname || `유저 #${line.user_id}` }}</p>
              <p>{{ line.content }}</p>

              <div class="comment-block">
                <p class="comment-title">댓글</p>
                <p v-if="!(commentsByUnderline[line.id] || []).length" class="empty">아직 댓글이 없습니다.</p>
                <ul v-else class="comment-list">
                  <li v-for="comment in commentsByUnderline[line.id]" :key="comment.id">
                    <strong>{{ usersById[comment.user_id]?.nickname || `유저 #${comment.user_id}` }}</strong>
                    <span>{{ comment.content }}</span>
                    <button
                      v-if="currentUser?.id === comment.user_id"
                      class="delete-btn"
                      :disabled="loadingUnderlines"
                      @click="handleDeleteComment(line.id, comment.id)"
                    >
                      삭제
                    </button>
                  </li>
                </ul>

                <div class="action-row comment-input-row">
                  <input
                    v-model="commentDraftByUnderline[line.id]"
                    type="text"
                    placeholder="댓글을 입력하세요"
                    @keyup.enter="handleAddComment(line.id)"
                  />
                  <button :disabled="loadingUnderlines" @click="handleAddComment(line.id)">댓글 등록</button>
                </div>
              </div>
            </article>
            <p v-if="underlines.length === 0" class="empty">밑줄 데이터가 없습니다.</p>
          </template>
        </div>
      </section>

      <section v-if="activeTab === 'reading'" class="editor-panel reading-panel">
        <h2>읽기 현황 보드</h2>
        <p class="meta">각 멤버의 현재 읽기 상태를 확인하고, 내 카드만 수정할 수 있습니다.</p>

        <div v-if="loadingReadingBoard" class="inline-loader-row">
          <div class="spinner small" aria-hidden="true"></div>
          <span class="meta">읽기 현황 불러오는 중...</span>
        </div>

        <div v-else class="reading-grid">
          <article v-for="item in readingBoard" :key="item.user.id" class="reading-card">
            <div class="reading-card-head">
              <strong>{{ item.user.nickname }}</strong>
              <span class="meta">{{ currentUser?.id === item.user.id ? '내 카드' : '읽기 전용' }}</span>
            </div>

            <div class="reading-form-row">
              <label>책</label>
              <select
                v-model="readingDraftByUser[item.user.id].current_book_id"
                :disabled="currentUser?.id !== item.user.id"
                @change="syncCurrentPageForDone(item.user.id)"
              >
                <option value="">선택 안함</option>
                <option v-for="book in books" :key="book.id" :value="book.id">{{ book.title }}</option>
              </select>
            </div>

            <div class="reading-form-row">
              <label>상태</label>
              <select
                v-model="readingDraftByUser[item.user.id].reading_status"
                :disabled="currentUser?.id !== item.user.id"
                @change="syncCurrentPageForDone(item.user.id)"
              >
                <option v-for="option in readingStatusOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>

            <div class="reading-form-row">
              <label>현재 페이지</label>
              <input
                v-model="readingDraftByUser[item.user.id].current_page"
                type="number"
                min="0"
                :disabled="currentUser?.id !== item.user.id"
              />
            </div>

            <div class="reading-form-row reading-page-row">
              <label>저장</label>
              <div></div>
              <button
                v-if="currentUser?.id === item.user.id"
                :disabled="loadingReadingBoard"
                @click="handleSaveReadingCard(item.user.id)"
              >
                저장
              </button>
            </div>

            <div class="reading-progress" v-if="getReadingProgressPercent(item) !== null">
              <div class="reading-progress-top">
                <span>진행률</span>
                <strong>{{ getReadingProgressPercent(item) }}%</strong>
              </div>
              <div class="reading-progress-track">
                <div class="reading-progress-bar" :style="{ width: `${getReadingProgressPercent(item)}%` }"></div>
              </div>
              <p class="meta">
                {{ item.user.current_page || 0 }} / {{ item.current_book?.total_pages }} 페이지
              </p>
            </div>
            <p v-else class="meta">진행률을 보려면 책의 총 페이지를 등록하세요.</p>

          </article>
        </div>

        <p v-if="readingMessage" class="meta-message">{{ readingMessage }}</p>
      </section>

      <section v-if="activeTab === 'admin'" class="editor-panel admin-panel">
        <h2>Admin 페이지</h2>
        <p class="meta">회원 관리와 책 추가를 할 수 있습니다.</p>

        <div class="admin-grid">
          <article class="admin-card">
            <h3>회원 관리</h3>
            <div class="action-row admin-user-row">
              <input
                v-model="adminUserNickname"
                type="text"
                placeholder="새 회원 닉네임"
                @keyup.enter="handleCreateUserByAdmin"
              />
              <input
                v-model="adminUserPassword"
                type="password"
                placeholder="초기 비밀번호"
                @keyup.enter="handleCreateUserByAdmin"
              />
              <button :disabled="loadingAdminAction" @click="handleCreateUserByAdmin">회원 추가</button>
            </div>
            <ul class="admin-list">
              <li v-for="user in users" :key="user.id">#{{ user.id }} · {{ user.nickname }}</li>
            </ul>
          </article>

          <article class="admin-card">
            <h3>책 추가</h3>
            <div class="admin-form">
              <input v-model="adminBookTitle" type="text" placeholder="책 제목" />
              <input v-model="adminBookAuthor" type="text" placeholder="저자" />
              <input v-model="adminBookTotalPages" type="number" min="1" placeholder="총 페이지(선택)" />
              <button :disabled="loadingAdminAction || loadingBooks" @click="handleCreateBookByAdmin">책 등록</button>
            </div>
            <ul class="admin-list">
              <li v-for="book in books" :key="book.id" class="admin-list-row">
                <span>#{{ book.id }} · {{ book.title }} ({{ book.author }}) · {{ book.total_pages || '-' }}p</span>
                <button class="delete-btn" :disabled="loadingAdminAction || loadingBooks" @click="handleDeleteBookByAdmin(book.id)">책 삭제</button>
              </li>
            </ul>
          </article>
        </div>

        <div v-if="loadingAdminAction" class="inline-loader-row">
          <div class="spinner small" aria-hidden="true"></div>
          <span class="meta">관리 작업 처리 중...</span>
        </div>

        <p v-if="adminMessage" class="meta-message">{{ adminMessage }}</p>
      </section>
    </section>
  </main>
</template>

<style scoped>
* {
  box-sizing: border-box;
}

.container {
  --primary: #96ba95;
  --primary-strong: #7ea97d;
  --primary-soft: #eaf2e9;
  --text-main: #1f2937;
  --text-sub: #6b7280;
  --line: #dfe7df;
  min-height: 100vh;
  padding: 16px;
  background: linear-gradient(180deg, #f6faf6 0%, #eef4ee 100%);
  color: var(--text-main);
}

.login-card {
  max-width: 520px;
  margin: 72px auto 0;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 26px;
  box-shadow: 0 12px 30px rgba(31, 41, 55, 0.08);
}

.initial-loader-wrap {
  min-height: 160px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.login-card h1 {
  margin: 0 0 10px;
  font-size: 30px;
  letter-spacing: -0.02em;
}

.login-row,
.action-row {
  display: flex;
  gap: 10px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.action-row > * {
  min-width: 0;
}

.underline-content-row input {
  width: 100%;
  flex: 1 1 100%;
}

.underline-comment-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
}

.underline-comment-row input {
  width: 100%;
  min-width: 0;
}

.underline-comment-row button {
  width: auto;
  white-space: nowrap;
}

p,
span,
strong,
li,
h1,
h2,
h3 {
  overflow-wrap: anywhere;
}

.login-row {
  flex-direction: column;
  align-items: stretch;
}

.login-inputs {
  display: flex;
  gap: 10px;
  width: 100%;
  flex-wrap: wrap;
}

.login-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  width: 100%;
  flex-wrap: wrap;
}

.meta-message {
  margin-top: 10px;
  color: var(--text-sub);
  font-size: 13px;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid #e5e7eb;
  border-top-color: var(--primary-strong);
  border-radius: 50%;
  animation: spin 0.85s linear infinite;
}

.spinner.small {
  width: 18px;
  height: 18px;
  border-width: 2px;
}

input,
select,
button {
  border: 1px solid #d3dfd3;
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 14px;
  line-height: 1.2;
}

input {
  flex: 1 1 220px;
  min-width: 0;
  background: #fff;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

select {
  background: #fff;
  min-width: 0;
}

input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(150, 186, 149, 0.2);
}

select:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(150, 186, 149, 0.2);
}

button {
  cursor: pointer;
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
  white-space: nowrap;
  transition: transform 0.12s ease, background-color 0.2s ease, border-color 0.2s ease;
}

button:hover:not(:disabled) {
  background: var(--primary-strong);
  border-color: var(--primary-strong);
  transform: translateY(-1px);
}

button:disabled {
  opacity: 0.62;
  cursor: not-allowed;
  transform: none;
}

.login-actions button {
  min-width: 96px;
}

.library-page {
  max-width: 1120px;
  margin: 0 auto;
}

.library-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #fff;
}

.tab-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.tab-btn {
  border: 1px solid var(--line);
  color: #3f4b45;
  background: #fff;
}

.tab-btn.active {
  background: var(--primary-strong);
  color: #fff;
  border-color: var(--primary-strong);
}

.bookshelf {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
  padding: 14px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid var(--line);
}

.book-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  border-radius: 12px;
  background: #f8fbf8;
  border: 1px solid #ecf1ec;
  cursor: pointer;
}

.skeleton-card,
.carousel-card {
  cursor: default;
  border-color: #e5e7eb;
}

.skeleton-block,
.skeleton-line {
  background: linear-gradient(90deg, #f1f5f9 20%, #e2e8f0 40%, #f1f5f9 60%);
  background-size: 220% 100%;
  animation: shimmer 1.1s ease-in-out infinite;
}

.skeleton-block {
  width: 32px;
  height: 32px;
  border-radius: 8px;
}

.skeleton-line {
  height: 12px;
  border-radius: 8px;
}

.skeleton-line.short {
  width: 55%;
}

.book-card.selected {
  border-color: var(--primary-strong);
  box-shadow: 0 0 0 2px rgba(150, 186, 149, 0.22);
}

.book-cover {
  font-size: 24px;
}

.book-card span,
.meta,
.empty,
.error {
  color: var(--text-sub);
}

.editor-panel {
  margin-top: 14px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 18px;
  box-shadow: 0 8px 24px rgba(31, 41, 55, 0.05);
}

.underline-list {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.underline-carousel-loader {
  overflow: hidden;
  width: 100%;
  border: 1px dashed #d7e2d7;
  border-radius: 12px;
  padding: 10px;
  background: #f8fbf8;
}

.carousel-track {
  display: flex;
  gap: 10px;
  width: max-content;
  animation: carouselSlide 1.8s linear infinite;
}

.carousel-card {
  width: 260px;
  min-height: 140px;
  border-radius: 10px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #fff;
}

.underline-item {
  border: 1px solid #e2ebe2;
  border-radius: 12px;
  padding: 12px;
  background: #fbfdfb;
}

.underline-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.author {
  margin: 4px 0;
  font-size: 13px;
  color: #4b5b53;
}

.comment-block {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed #dfe8df;
}

.comment-title {
  margin: 0 0 6px;
  font-size: 13px;
  color: #4b5b53;
}

.comment-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.comment-list li {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 13px;
  color: #334155;
}

.delete-btn {
  margin-left: auto;
  font-size: 12px;
  padding: 4px 8px;
  border: 1px solid #ef4444;
  color: #ef4444;
  background: #fff;
}

.delete-btn:hover:not(:disabled) {
  background: #fff5f5;
  border-color: #dc2626;
  color: #dc2626;
}

.admin-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.reading-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.reading-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}

.reading-card {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px;
  background: #f9fcf9;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.reading-card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.reading-form-row {
  display: grid;
  grid-template-columns: 68px minmax(0, 1fr);
  align-items: center;
  gap: 6px;
}

.reading-form-row label {
  font-size: 12px;
  color: var(--text-sub);
}

.reading-page-row {
  grid-template-columns: 68px minmax(0, 1fr) auto;
}

.reading-page-row button {
  width: auto;
  padding: 6px 10px;
  white-space: nowrap;
}

.reading-progress {
  border: 1px solid #e2ebe2;
  border-radius: 10px;
  padding: 8px;
  background: #fff;
}

.reading-progress-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  margin-bottom: 6px;
}

.reading-progress-track {
  width: 100%;
  height: 8px;
  border-radius: 999px;
  background: #eaf2e9;
  overflow: hidden;
}

.reading-progress-bar {
  height: 100%;
  background: #96ba95;
}

.admin-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}

.admin-card {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px;
  background: #f9fcf9;
}

.admin-card h3 {
  margin: 0 0 8px;
  font-size: 16px;
}

.admin-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.admin-list {
  margin: 10px 0 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #4b5b53;
}

.admin-list-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.inline-loader-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes shimmer {
  to {
    background-position: -220% 0;
  }
}

@keyframes carouselSlide {
  from {
    transform: translateX(0);
  }
  to {
    transform: translateX(-270px);
  }
}

@media (max-width: 768px) {
  .container {
    padding: 12px;
  }

  input {
    font-size: 13px;
    padding: 7px 9px;
    border-radius: 9px;
  }

  select {
    font-size: 13px;
    padding: 7px 9px;
    border-radius: 9px;
  }

  .login-card {
    margin-top: 12px;
    max-width: 360px;
    padding: 10px;
    border-radius: 14px;
  }

  .login-card h1 {
    font-size: 20px;
    margin-bottom: 4px;
  }

  .login-card p {
    display: none;
  }

  .login-card input,
  .login-card button {
    font-size: 13px;
    padding: 8px 10px;
    border-radius: 9px;
  }

  .login-row {
    gap: 6px;
  }

  .login-inputs {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .login-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .login-inputs input,
  .login-actions button {
    width: 100%;
    min-width: 0;
  }

  .action-row {
    flex-direction: row;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }

  .action-row input {
    flex: 1 1 100%;
    width: 100%;
    max-width: 100%;
  }

  .action-row button {
    width: 100%;
    flex: 1 1 100%;
    padding: 7px 10px;
  }

  .page-query-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: 8px;
    flex-wrap: nowrap;
  }

  .page-query-row input {
    width: 100%;
    min-width: 0;
  }

  .page-query-row button {
    width: auto;
    max-width: 100%;
    flex: 0 0 auto;
    white-space: nowrap;
  }

  .comment-input-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: 8px;
    flex-wrap: nowrap;
  }

  .comment-input-row input {
    width: 100%;
    min-width: 0;
  }

  .comment-input-row button {
    width: auto;
    max-width: 100%;
    flex: 0 0 auto;
    white-space: nowrap;
  }

  .underline-content-row,
  .underline-comment-row {
    display: block;
  }

  .underline-content-row input,
  .underline-comment-row input {
    width: 100%;
    max-width: 100%;
  }

  .underline-comment-row button {
    display: block;
    width: 100%;
    max-width: 100%;
    margin-top: 6px;
    white-space: normal;
  }

  .admin-user-row,
  .admin-form {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 8px;
    align-items: center;
  }

  .admin-user-row input,
  .admin-form input {
    width: 100%;
    min-width: 0;
  }

  .admin-user-row button,
  .admin-form button {
    width: 100%;
    flex: 1 1 100%;
  }

  .underline-comment-row {
    gap: 8px;
  }

  .library-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .bookshelf {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .carousel-card {
    width: 220px;
  }
}

@media (max-width: 520px) {
  .container {
    padding: 10px;
  }

  input {
    font-size: 12px;
    padding: 6px 8px;
  }

  select {
    font-size: 12px;
    padding: 6px 8px;
  }

  .login-card {
    margin-top: 8px;
    max-width: 320px;
    padding: 8px;
  }

  .login-card h1 {
    font-size: 18px;
  }

  .login-card input,
  .login-card button {
    padding: 6px 8px;
    font-size: 12px;
  }

  .login-inputs,
  .login-actions {
    gap: 4px;
  }

  .action-row {
    gap: 6px;
  }

  .action-row button {
    padding: 6px 8px;
  }

  .page-query-row {
    gap: 6px;
  }

  .comment-input-row {
    gap: 6px;
  }

  .underline-comment-row,
  .admin-user-row,
  .admin-form {
    gap: 6px;
  }

  .bookshelf {
    grid-template-columns: 1fr;
  }

  .reading-grid {
    grid-template-columns: 1fr;
  }

  .reading-form-row {
    grid-template-columns: 60px minmax(0, 1fr);
    gap: 4px;
  }

  .reading-page-row {
    grid-template-columns: 60px minmax(0, 1fr) auto;
  }

  .reading-page-row button {
    padding: 5px 8px;
  }

  .editor-panel,
  .library-header {
    padding: 14px;
  }
}

@media (max-width: 380px) {
  .login-inputs,
  .login-actions {
    grid-template-columns: 1fr;
  }
}
</style>
