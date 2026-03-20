<script setup>
import { computed, onMounted, ref, watch } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE || '/api'

const isLoggedIn = ref(false)
const loginNickname = ref('')
const currentUser = ref(null)

const users = ref([])
const books = ref([])
const selectedBookId = ref(null)
const pageFilter = ref('')
const underlineInput = ref('')
const underlines = ref([])
const errorMessage = ref('')
const loading = ref(false)

const selectedBook = computed(() =>
  books.value.find((book) => book.id === selectedBookId.value) ?? null,
)

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    throw new Error(`요청 실패: ${response.status}`)
  }
  if (response.status === 204) return null
  return response.json()
}

async function loadUsers() {
  users.value = await request('/users')
}

async function ensureDisplayBooks() {
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
}

async function loadUnderlines() {
  if (!selectedBookId.value) {
    underlines.value = []
    return
  }
  const query = pageFilter.value ? `?page=${pageFilter.value}` : ''
  underlines.value = await request(`/underlines/book/${selectedBookId.value}${query}`)
}

async function handleLogin() {
  if (!loginNickname.value.trim()) return
  try {
    loading.value = true
    errorMessage.value = ''
    await loadUsers()

    const found = users.value.find((user) => user.nickname === loginNickname.value.trim())
    if (found) {
      currentUser.value = found
    } else {
      currentUser.value = await request('/users', {
        method: 'POST',
        body: JSON.stringify({ nickname: loginNickname.value.trim() }),
      })
      await loadUsers()
    }

    isLoggedIn.value = true
    await ensureDisplayBooks()
    await loadUnderlines()
  } catch (error) {
    errorMessage.value = '로그인에 실패했습니다. 백엔드 서버를 확인해주세요.'
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
    }),
  })

  underlineInput.value = ''
  await loadUnderlines()
}

function handleLogout() {
  isLoggedIn.value = false
  currentUser.value = null
  loginNickname.value = ''
  underlines.value = []
}

watch(selectedBookId, async () => {
  if (isLoggedIn.value) {
    await loadUnderlines()
  }
})

onMounted(async () => {
  try {
    await ensureDisplayBooks()
  } catch {
    errorMessage.value = '초기 데이터 로딩에 실패했습니다.'
  }
})
</script>

<template>
  <main class="container">
    <section v-if="!isLoggedIn" class="login-card">
      <h1>meet-zool</h1>
      <p>교환독서 서재에 입장하려면 닉네임으로 로그인하세요.</p>
      <div class="login-row">
        <input v-model="loginNickname" type="text" placeholder="닉네임 입력" @keyup.enter="handleLogin" />
        <button :disabled="loading" @click="handleLogin">로그인</button>
      </div>
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

      <section class="bookshelf">
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
      </section>

      <section v-if="selectedBook" class="editor-panel">
        <h2>{{ selectedBook.title }}</h2>

        <div class="action-row">
          <input v-model="pageFilter" type="number" min="1" placeholder="페이지 번호" />
          <button @click="loadUnderlines">페이지 조회</button>
        </div>

        <div class="action-row">
          <input v-model="underlineInput" type="text" placeholder="밑줄 내용을 입력하세요" @keyup.enter="handleAddUnderline" />
          <button @click="handleAddUnderline">밑줄 저장</button>
        </div>

        <div class="underline-list">
          <article v-for="line in underlines" :key="line.id" class="underline-item">
            <p class="meta">페이지 {{ line.page }}</p>
            <p>{{ line.content }}</p>
          </article>
          <p v-if="underlines.length === 0" class="empty">밑줄 데이터가 없습니다.</p>
        </div>
      </section>
    </section>
  </main>
</template>

<style scoped>
.container {
  min-height: 100vh;
  padding: 24px;
  background: #f3f4f6;
}

.login-card {
  max-width: 480px;
  margin: 120px auto 0;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 24px;
}

.login-card h1 {
  margin: 0 0 10px;
}

.login-row,
.action-row {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

input,
button {
  border: 1px solid #d1d5db;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 14px;
}

input {
  flex: 1;
}

button {
  cursor: pointer;
  background: #fff;
}

.library-page {
  max-width: 1100px;
  margin: 0 auto;
}

.library-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.bookshelf {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  padding: 18px;
  border-radius: 14px;
  background:
    linear-gradient(to bottom, rgba(120, 74, 33, 0.14), rgba(120, 74, 33, 0.2)),
    repeating-linear-gradient(
      to bottom,
      #f6e8d5 0,
      #f6e8d5 72px,
      #d4a373 72px,
      #d4a373 80px
    );
  border: 1px solid #e5d6c6;
}

.book-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid transparent;
  cursor: pointer;
}

.book-card.selected {
  border-color: #111827;
}

.book-cover {
  font-size: 24px;
}

.book-card span,
.meta,
.empty,
.error {
  color: #6b7280;
}

.editor-panel {
  margin-top: 16px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 18px;
}

.underline-list {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.underline-item {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px;
  background: #fafafa;
}

@media (max-width: 768px) {
  .container {
    padding: 12px;
  }

  .library-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>
