<script setup>
import { ref, computed, nextTick, onBeforeUnmount } from 'vue'
import { useAuth } from '#imports'

const { token } = useAuth()

// ==============================================
// STATO GENERALE DEL QUIZ
// ==============================================
const quizState = ref('intro') 
const currentQuestionIndex = ref(0)
const score = ref(0)
const attemptsLeft = ref(3)
const feedbackMessage = ref('')
const feedbackType = ref('') 
const errorMessage = ref('') 
const isInfoModalOpen = ref(false)
const isCameraInfoModalOpen = ref(false)
const selectedCategories = ref([])
const questions = ref([])
const feedbackHints = ref([])
let feedbackTimeout = null

const quizCategories = ref([
  { id: 'alphabet', title: 'Alphabet', description: 'Practice single letters of the alphabet.', icon: 'i-lucide-case-sensitive' },
  { id: 'animals', title: 'Animals', description: 'All terms related to animals and insects.', icon: 'i-lucide-paw-print' },
  { id: 'actions', title: 'Actions & Verbs', description: 'Physical actions, interactions, and movements.', icon: 'i-lucide-activity' },
  { id: 'food', title: 'Food & Drinks', description: 'Food items, snacks, and beverages.', icon: 'i-lucide-utensils' },
  { id: 'home', title: 'Home & Rooms', description: 'Rooms of the house, furniture, and household items.', icon: 'i-lucide-home' },
  { id: 'objects', title: 'Objects & Toys', description: 'Everyday objects, toys, and small tools.', icon: 'i-lucide-package' },
  { id: 'transport', title: 'Transport', description: 'Vehicles and modes of transportation.', icon: 'i-lucide-car' },
  { id: 'people_professions', title: 'Family, People & Professions', description: 'Family members, professions, and general terms for people.', icon: 'i-lucide-users' },
  { id: 'body', title: 'Body Parts', description: 'Anatomy and body parts.', icon: 'i-lucide-user' },
  { id: 'colors', title: 'Colors', description: 'Colors and shades.', icon: 'i-lucide-palette' },
  { id: 'nature', title: 'Nature & Places', description: 'Nature, weather, and physical spaces.', icon: 'i-lucide-tree-pine' },
  { id: 'clothing', title: 'Clothing', description: 'Apparel and accessories.', icon: 'i-lucide-shirt' },
  { id: 'emotions', title: 'Emotions, States & Adjectives', description: 'Feelings, conditions, and descriptive attributes.', icon: 'i-lucide-smile' },
  { id: 'greetings', title: 'Greetings & Manners', description: 'Polite expressions, greetings, and basic communication.', icon: 'i-lucide-message-circle-heart' },
  { id: 'other', title: 'Time, Questions, Adverbs & Other', description: 'Time concepts, pronouns, adverbs, and grammar words.', icon: 'i-lucide-help-circle' }
])

const mixedCategory = {
  id: 'mixed',
  title: 'Mixed',
  description: 'Play with every unlocked sign across the whole dictionary.',
  icon: 'i-lucide-shuffle'
}

const hasSelectedCategories = computed(() => selectedCategories.value.length > 0)
const isMixedSelected = computed(() => selectedCategories.value.includes(mixedCategory.id))

const selectMixedCategory = () => {
  selectedCategories.value = [mixedCategory.id]
  errorMessage.value = ''
}

const toggleCategory = (id) => {
  if (isMixedSelected.value) {
    selectedCategories.value = [id]
    errorMessage.value = ''
    return
  }

  if (selectedCategories.value.includes(id)) {
    selectedCategories.value = selectedCategories.value.filter(categoryId => categoryId !== id)
  } else {
    selectedCategories.value = [...selectedCategories.value, id]
  }
  errorMessage.value = '' // Pulisce istantaneamente l'errore quando si cambia scheda
}
const currentQuestion = computed(() => questions.value.length > 0 ? questions.value[currentQuestionIndex.value] : null)

// ==============================================
// LOGICA WEBCAM & MEDIAPIPE (REPLICATA DA CHATBOT)
// ==============================================
const isCameraActive = ref(false)
const isPredicting = ref(false)
const showLandmarks = ref(true)
const showHint = ref(false)
const appState = ref('IDLE')

const videoElement = ref(null)
const canvasElement = ref(null)
const canvasCtx = ref(null)

const signFrames = ref([])
const MIN_FRAMES = 15

// Allineamento del campionamento frame per non distorcere l'inferenza temporale di TF
const maxFrames = computed(() => currentQuestion.value?.level === 'level_1' ? 150 : 384)

let holistic = null
let camera = null
let drawingUtils = null
let mpHolistic = null

const onResults = (results) => {
  if (canvasCtx.value && canvasElement.value && drawingUtils && mpHolistic) {
    canvasCtx.value.save()
    canvasCtx.value.clearRect(0, 0, canvasElement.value.width, canvasElement.value.height)
    if (showLandmarks.value) {
      if (results.faceLandmarks) drawingUtils.drawLandmarks(canvasCtx.value, results.faceLandmarks, { color: '#648214', lineWidth: 1, radius: 1 })
      if (results.poseLandmarks) {
        drawingUtils.drawConnectors(canvasCtx.value, results.poseLandmarks, mpHolistic.POSE_CONNECTIONS, { color: '#1E50C8', lineWidth: 2 })
        drawingUtils.drawLandmarks(canvasCtx.value, results.poseLandmarks, { color: '#1E50C8', lineWidth: 2, radius: 3 })
      }
      if (results.leftHandLandmarks) {
        drawingUtils.drawConnectors(canvasCtx.value, results.leftHandLandmarks, mpHolistic.HAND_CONNECTIONS, { color: '#C81E64', lineWidth: 2 })
        drawingUtils.drawLandmarks(canvasCtx.value, results.leftHandLandmarks, { color: '#C81E64', lineWidth: 2, radius: 3 })
      }
      if (results.rightHandLandmarks) {
        drawingUtils.drawConnectors(canvasCtx.value, results.rightHandLandmarks, mpHolistic.HAND_CONNECTIONS, { color: '#C81E64', lineWidth: 2 })
        drawingUtils.drawLandmarks(canvasCtx.value, results.rightHandLandmarks, { color: '#C81E64', lineWidth: 2, radius: 3 })
      }
    }
    canvasCtx.value.restore()
  }

  if (appState.value === 'BUFFERING') {
    if (signFrames.value.length < maxFrames.value) {
      const frameData = Array(543).fill([null, null, null])
      if (results.faceLandmarks) results.faceLandmarks.forEach((lm, i) => frameData[i] = [lm.x, lm.y, lm.z])
      if (results.leftHandLandmarks) results.leftHandLandmarks.forEach((lm, i) => frameData[468 + i] = [lm.x, lm.y, lm.z])
      if (results.poseLandmarks) results.poseLandmarks.forEach((lm, i) => frameData[489 + i] = [lm.x, lm.y, lm.z])
      if (results.rightHandLandmarks) results.rightHandLandmarks.forEach((lm, i) => frameData[522 + i] = [lm.x, lm.y, lm.z])
      signFrames.value.push(frameData)
    }
    if (signFrames.value.length === maxFrames.value && !isPredicting.value) {
      submitSign()
    }
  }
}

const activateCamera = async () => {
  if (document.activeElement?.blur) document.activeElement.blur()
  isCameraActive.value = true
  appState.value = 'IDLE'
  signFrames.value = []
  
  await nextTick()
  if (canvasElement.value) canvasCtx.value = canvasElement.value.getContext('2d')

  if (import.meta.client && videoElement.value) {
    try {
      mpHolistic = await import('@mediapipe/holistic')
      const { Camera } = await import('@mediapipe/camera_utils')
      drawingUtils = await import('@mediapipe/drawing_utils')

      holistic = new mpHolistic.Holistic({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/holistic/${file}`
      })
      holistic.setOptions({
        modelComplexity: 1, smoothLandmarks: true, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5
      })
      holistic.onResults(onResults)

      camera = new Camera(videoElement.value, {
        onFrame: async () => {
          if (isCameraActive.value && videoElement.value) {
            if (canvasElement.value && canvasElement.value.width !== videoElement.value.videoWidth) {
              canvasElement.value.width = videoElement.value.videoWidth
              canvasElement.value.height = videoElement.value.videoHeight
            }
            await holistic.send({ image: videoElement.value })
          }
        },
        width: 1280, height: 720
      })
      camera.start()
      window.addEventListener('keydown', handleKeyboard)
    } catch (err) {
      console.error("Errore inizializzazione MediaPipe:", err)
    }
  }
}

const stopCamera = () => {
  isCameraActive.value = false
  window.removeEventListener('keydown', handleKeyboard)
  if (camera) { camera.stop(); camera = null }
  if (holistic) { holistic.close(); holistic = null }
}

const startBuffering = () => {
  clearFeedbackTimeout()
  signFrames.value = []
  feedbackMessage.value = ''
  feedbackType.value = ''
  appState.value = 'BUFFERING'
}

const stopBufferingEarly = () => {
  if (appState.value === 'BUFFERING') {
    if (signFrames.value.length >= MIN_FRAMES) {
      submitSign() // Nel quiz submitSign non richiede parametri
    } else {
      appState.value = 'IDLE'
      signFrames.value = []
    }
  }
}

const clearFeedbackTimeout = () => {
  if (feedbackTimeout) {
    clearTimeout(feedbackTimeout)
    feedbackTimeout = null
  }
}

const scheduleErrorFeedbackDismiss = () => {
  clearFeedbackTimeout()
  feedbackTimeout = setTimeout(() => {
    if (feedbackType.value === 'error') {
      feedbackMessage.value = ''
      feedbackType.value = ''
      feedbackHints.value = []
    }
    feedbackTimeout = null
  }, 4000)
}

const submitSign = async () => {
  if (signFrames.value.length < MIN_FRAMES) return
  isPredicting.value = true
  const framesToSend = [...signFrames.value]
  signFrames.value = []

  const targetUrl = currentQuestion.value.level === 'level_1'
    ? 'http://127.0.0.1:8000/recognize-letter' 
    : 'http://127.0.0.1:8000/recognize-sign'

  try {
    const response = await $fetch(targetUrl, {
      method: 'POST',
      headers: { 'Authorization': token.value },
      body: { frames: framesToSend, target_word: currentQuestion.value.targetWord }
    })

    appState.value = 'IDLE'
    const confidencePercent = Math.round(response.confidence * 100)

    if (response.is_correct) {
      feedbackType.value = 'success'
      feedbackMessage.value = `Correct! AI recognized "${response.predicted_word}" (${confidencePercent}%).`
      feedbackHints.value = []
      score.value++
      stopCamera()
      setTimeout(nextQuestion, 2000)
    } else {
      attemptsLeft.value--
      feedbackType.value = 'error'
      feedbackHints.value = response.feedback || []
      
      if (attemptsLeft.value > 0) {
        feedbackMessage.value = `Wrong sign. AI detected "${response.predicted_word}" (${confidencePercent}%). You have ${attemptsLeft.value} attempt(s) left. Try again by pressing [N].`
      } else {
        feedbackMessage.value = `Out of attempts! AI detected "${response.predicted_word}" (${confidencePercent}%). Moving to the next question.`
        stopCamera()
        setTimeout(nextQuestion, 2500)
      }
      scheduleErrorFeedbackDismiss()
    }
  } catch (error) {
    console.error("Errore di inferenza:", error)
    appState.value = 'IDLE'
  } finally {
    isPredicting.value = false
  }
}

const handleKeyboard = (e) => {
  if (!isCameraActive.value) return
  const key = e.key.toLowerCase()
  if (key === 'n' && appState.value === 'IDLE') {
    e.preventDefault()
    startBuffering()
  } else if (key === ' ' && appState.value === 'BUFFERING') {
    e.preventDefault()
    if (signFrames.value.length >= MIN_FRAMES) submitSign()
  } else if (key === 'l') {
    e.preventDefault()
    showLandmarks.value = !showLandmarks.value
  } else if (key === 'q') {
    e.preventDefault()
    stopCamera()
  }
}

// ==============================================
// GESTIONE FLUSSO DOMANDE
// ==============================================
const startQuiz = async () => {
  if (!hasSelectedCategories.value) return
  
  errorMessage.value = ''
  try {
    const categoriesParam = selectedCategories.value.map(category => encodeURIComponent(category)).join(',')
    // Chiamata corretta all'endpoint '/api/quiz/start' per evitare il 404
    const response = await $fetch(`http://localhost:8000/api/quiz/start?categories=${categoriesParam}`, {
      method: 'GET',
      headers: { 'Authorization': token.value }
    })

    // Se i segni sbloccati sono insufficienti, il backend restituisce lo status 'error'
    if (response.status === 'error' && response.code === 'INSUFFICIENT_SIGNS') {
      errorMessage.value = response.message
      return
    }

    // Mappatura e formattazione dei quesiti se la validazione ha esito positivo
    questions.value = response.questions.map(q => {
      let textPrompt = 'Which word corresponds to this sign?'
      if (q.type === 'recognition') {
        textPrompt = 'Perform the following sign in front of the camera:'
      } else if (q.type === 'word-sign') {
        textPrompt = 'Which sign corresponds to this word?'
      }

      return {
        id: q.question_index,
        type: q.type,
        questionText: textPrompt,
        targetWord: q.target_word,
        targetMedia: q.target_media,
        level: q.level,
        options: q.options.map((opt, i) => ({
          id: ['A', 'B', 'C', 'D'][i],
          label: opt.toUpperCase(),
          content: opt,
          isCorrect: opt.toLowerCase() === q.target_word.toLowerCase()
        }))
      }
    })

    quizState.value = 'playing'
    currentQuestionIndex.value = 0
    score.value = 0
    
    nextTick(() => {
      resetQuestionState()
    })

  } catch (err) {
    console.error("Errore durante la generazione del quiz:", err)
    errorMessage.value = "An error occurred while generating the quiz. Please try again."
  }
}

const sendFinalScore = async () => {
  try {
    await $fetch('http://localhost:8000/api/quiz/submit', {
      method: 'POST',
      headers: { 'Authorization': token.value, 'Content-Type': 'application/json' },
      body: { score: score.value }
    })
  } catch (err) {
    console.error("Error saving score:", err)
  }
}

const resetQuestionState = () => {
  clearFeedbackTimeout()
  attemptsLeft.value = 5
  feedbackMessage.value = ''
  feedbackType.value = ''
  feedbackHints.value = []
  showHint.value = false
  stopCamera()
}

const handleAnswer = (option) => {
  if (feedbackType.value === 'success' || attemptsLeft.value === 0) return
  if (option.isCorrect) {
    feedbackType.value = 'success'
    feedbackMessage.value = 'Correct! Great job.'
    score.value++
    setTimeout(nextQuestion, 1500)
  } else {
    attemptsLeft.value--
    if (attemptsLeft.value > 0) {
      feedbackType.value = 'error'
      feedbackMessage.value = `Wrong. You have ${attemptsLeft.value} attempt(s) left.`
      scheduleErrorFeedbackDismiss()
    } else {
      feedbackType.value = 'error'
      feedbackMessage.value = 'Out of attempts! Moving to the next question.'
      setTimeout(nextQuestion, 2500)
      scheduleErrorFeedbackDismiss()
    }
  }
}

const nextQuestion = () => {
  if (currentQuestionIndex.value < questions.value.length - 1) {
    currentQuestionIndex.value++
    resetQuestionState()
  } else {
    quizState.value = 'result'
    sendFinalScore()
  }
}

const skipQuestion = () => {
  feedbackType.value = 'info'
  feedbackMessage.value = 'Question skipped. Moving to the next one...'
  stopCamera()
  setTimeout(nextQuestion, 1500)
}

const resetQuizToIntro = () => {
  stopCamera()
  quizState.value = 'intro'
  questions.value = []
  currentQuestionIndex.value = 0
  score.value = 0
  resetQuestionState()
}

const exitQuiz = () => {
  const isConfirmed = confirm("Are you sure you want to exit the quiz? Your current progress will be lost.")
  if (!isConfirmed) return

  resetQuizToIntro()
}

onBeforeUnmount(() => {
  clearFeedbackTimeout()
  stopCamera()
})
</script>

<template>
  <div>
    <div class="flex min-h-[calc(100vh-140px)] bg-white dark:bg-transparent transition-colors duration-200">
      
      <AppSidebar />

      <div class="flex-1 px-4 lg:px-8 py-8 w-full max-w-7xl mx-auto relative flex flex-col">
        <div class="w-full flex flex-col gap-6 flex-1">

          <div v-if="quizState === 'intro'" class="w-full flex flex-col gap-8">
            
            <div id="tour-quiz-header" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5 flex items-center justify-between shadow-sm w-full">
              <div class="flex items-center gap-4">
                <div class="bg-primary-100 dark:bg-primary-900/30 p-3 rounded-lg flex-shrink-0 flex items-center justify-center">
                  <UIcon name="i-lucide-brain" class="w-8 h-8 text-primary-600 dark:text-primary-400" />
                </div>
                <div>
                  <div class="flex items-center gap-2">
                    <h1 class="text-2xl font-extrabold text-gray-900 dark:text-white tracking-tight">Quiz</h1>
                    <UButton 
                      icon="i-lucide-info" 
                      color="primary" 
                      variant="ghost" 
                      size="xs" 
                      class="rounded-full hover:scale-110 transition-transform" 
                      @click="isInfoModalOpen = true" 
                    />
                  </div>
                  <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Test yourself to consolidate the signs you have learned. Choose one or more categories to start.</p>
                </div>
              </div>
            </div>

            <div class="mt-4 w-full">
              <h2 class="text-xl font-bold mb-6 text-gray-800 dark:text-gray-200">Play Everything</h2>
              <UCard
                class="cursor-pointer transition-all duration-200 group border-2"
                :class="[
                  isMixedSelected
                  ? 'border-primary-500 bg-primary-50/50 dark:bg-primary-900/20 shadow-md ring-1 ring-primary-500'
                  : 'border-gray-200 dark:border-gray-800 hover:border-primary-300 dark:hover:border-primary-700 hover:shadow-sm'
                ]"
                :ui="{ body: 'p-6 sm:p-8', rounded: 'rounded-2xl' }"
                @click="selectMixedCategory"
              >
                <div class="flex items-start gap-5">
                  <div
                    class="p-4 rounded-full transition-colors"
                    :class="[
                      isMixedSelected
                      ? 'bg-primary-500 text-white'
                      : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 group-hover:bg-primary-100 dark:group-hover:bg-primary-900/50 group-hover:text-primary-600'
                    ]"
                  >
                    <UIcon :name="mixedCategory.icon" class="w-8 h-8" />
                  </div>
                  <div>
                    <h3
                      class="text-xl font-bold transition-colors"
                      :class="isMixedSelected ? 'text-primary-700 dark:text-primary-400' : 'text-gray-900 dark:text-white group-hover:text-primary-600'"
                    >
                      {{ mixedCategory.title }}
                    </h3>
                    <p class="text-base text-gray-500 dark:text-gray-400 mt-2 leading-relaxed">
                      {{ mixedCategory.description }}
                    </p>
                  </div>
                </div>
              </UCard>
            </div>

            <div class="mt-4 w-full">
              <h2 class="text-xl font-bold mb-6 text-gray-800 dark:text-gray-200">Select Categories</h2>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <UCard
                  v-for="level in quizCategories"
                  :key="level.id"
                  class="cursor-pointer transition-all duration-200 group border-2"
                  :class="[
                    selectedCategories.includes(level.id)
                    ? 'border-primary-500 bg-primary-50/50 dark:bg-primary-900/20 shadow-md ring-1 ring-primary-500'
                    : 'border-gray-200 dark:border-gray-800 hover:border-primary-300 dark:hover:border-primary-700 hover:shadow-sm'
                  ]"
                  :ui="{ body: 'p-6 sm:p-8', rounded: 'rounded-2xl' }"
                  @click="toggleCategory(level.id)"
                >
                  <div class="flex items-start gap-5">
                    <div 
                      class="p-4 rounded-full transition-colors"
                      :class="[
                        selectedCategories.includes(level.id)
                        ? 'bg-primary-500 text-white'
                        : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 group-hover:bg-primary-100 dark:group-hover:bg-primary-900/50 group-hover:text-primary-600'
                      ]"
                    >
                      <UIcon :name="level.icon" class="w-8 h-8" />
                    </div>
                    <div>
                      <h3 
                        class="text-xl font-bold transition-colors"
                        :class="selectedCategories.includes(level.id) ? 'text-primary-700 dark:text-primary-400' : 'text-gray-900 dark:text-white group-hover:text-primary-600'"
                      >
                      {{ level.title }}
                      </h3>
                      <p class="text-base text-gray-500 dark:text-gray-400 mt-2 leading-relaxed">
                      {{ level.description }}
                      </p>
                    </div>
                  </div>
                </UCard>

              </div>
            </div>

            <div v-if="errorMessage" class="max-w-md mx-auto mt-6 text-left">
              <UAlert
                color="red"
                variant="soft"
                icon="i-lucide-alert-triangle"
                title="Requirement Error"
                :description="errorMessage"
              />
            </div>

            <div class="flex justify-center mt-8">
              <UButton 
                size="xl" 
                :color="hasSelectedCategories ? 'primary' : 'gray'"
                variant="solid" 
                class="px-12 py-4 text-xl font-bold shadow-md transition-all" 
                :class="{ 'opacity-50 cursor-not-allowed': !hasSelectedCategories, 'hover:scale-105': hasSelectedCategories }"
                :disabled="!hasSelectedCategories"
                :ui="{ rounded: 'rounded-xl' }"
                @click="startQuiz"
              > 
              Start Quiz
              </UButton>
            </div>

          </div>

          <div v-else-if="quizState === 'playing'" class="w-full max-w-5xl mx-auto flex flex-col flex-1 justify-center">
            <div class="mb-6">
              <div class="flex items-center justify-between gap-3 text-base font-bold text-gray-500 mb-2 px-1">
                <span>Question {{ currentQuestionIndex + 1 }} of {{ questions.length }}</span>
                <div class="flex items-center gap-3">
                  <span class="text-primary-600 dark:text-primary-400">Score: {{ score }}</span>
                  <UButton
                    color="red"
                    variant="soft"
                    size="sm"
                    icon="i-lucide-log-out"
                    class="font-bold px-4 py-2 rounded-xl border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300 shadow-sm transition-all hover:scale-105 hover:bg-red-100 dark:hover:bg-red-900/40 hover:shadow-md"
                    @click="exitQuiz"
                  >
                    Exit Quiz
                  </UButton>
                </div>
              </div>
              <UProgress :value="(currentQuestionIndex / questions.length) * 100" color="primary" size="sm" />
            </div>

            <UCard class="w-full flex-1 shadow-xl border-t-8 border-t-primary-500 rounded-2xl flex flex-col" :ui="{ body: 'p-6 sm:p-8 flex flex-col justify-center flex-1' }">
              <template #header>
                <h2 class="text-xl md:text-3xl font-extrabold text-center py-2 text-gray-900 dark:text-white leading-tight">
                  {{ currentQuestion.questionText }}
                </h2>
              </template>

              <div v-if="currentQuestion.type === 'word-sign'" class="flex flex-col items-center gap-8 py-4 w-full">
                <h3 class="text-3xl md:text-4xl font-black text-primary-600 dark:text-primary-400 tracking-widest uppercase bg-primary-50 dark:bg-primary-950/30 px-8 py-4 rounded-xl border border-primary-200 dark:border-primary-800">
                  {{ currentQuestion.targetWord }}
                </h3>
                
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-6 w-full max-w-2xl">
                  <UCard 
                    v-for="option in currentQuestion.options" 
                    :key="option.id"
                    class="cursor-pointer hover:border-primary-500 hover:shadow-lg transition-all text-center bg-gray-50 dark:bg-gray-800/50 rounded-xl overflow-hidden border-2 border-transparent"
                    @click="handleAnswer(option)"
                  >
                    <div class="relative py-4 flex items-center justify-center min-h-[200px] md:min-h-[240px] bg-white dark:bg-gray-900 rounded-lg p-2 shadow-inner">
                      <img 
                        :src="`http://localhost:8000/gif_output/${option.content.toLowerCase()}.gif`" 
                        alt="Sign Option" 
                        class="h-44 md:h-48 w-full object-contain mx-auto transition-transform hover:scale-105"
                      />
                    </div>
                    <p class="font-extrabold text-lg mt-3 text-gray-700 dark:text-gray-300 border-t border-gray-100 dark:border-gray-700 pt-2">
                      Option {{ option.id }}
                    </p>
                  </UCard>
                </div>

                <div class="flex justify-center mt-2">
                  <UButton 
                    color="gray" 
                    variant="soft" 
                    icon="i-lucide-fast-forward" 
                    class="font-bold py-2 px-6 rounded-xl transition-all hover:scale-105 hover:bg-gray-200 dark:hover:bg-gray-800" 
                    @click="skipQuestion"
                  >
                    Skip Question
                  </UButton>
                </div>
              </div>

              <div v-if="currentQuestion.type === 'sign-word'" class="flex flex-col items-center gap-8 py-4 w-full">
                
                <UCard class="w-full max-w-2xl aspect-video flex items-center justify-center bg-gray-100 dark:bg-gray-900 relative rounded-2xl border-2 border-gray-200 dark:border-gray-800 overflow-hidden shadow-md">
                  <img 
                    v-if="currentQuestion.targetMedia.startsWith('http')" 
                    :src="currentQuestion.targetMedia" 
                    alt="Sign Animation"
                    class="w-full h-full object-contain"
                  />
                  <UIcon 
                    v-else 
                    :name="currentQuestion.targetMedia" 
                    class="w-32 h-32 md:w-40 md:h-40 text-gray-700 dark:text-gray-300 mx-auto" 
                  />
                </UCard>
                
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-xl">
                  <UButton 
                    v-for="option in currentQuestion.options" 
                    :key="option.id"
                    size="lg" color="gray" variant="outline"
                    class="justify-center text-lg md:text-xl font-bold py-4 rounded-xl border-2 border-gray-300 dark:border-gray-700 hover:border-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/30 hover:text-primary-600 hover:shadow-lg transition-all shadow-sm"
                    @click="handleAnswer(option)"
                  >
                    {{ option.label }}
                  </UButton>
                </div>

                <div class="flex justify-center mt-2">
                  <UButton 
                    color="gray" 
                    variant="soft" 
                    icon="i-lucide-fast-forward" 
                    class="font-bold py-2 px-6 rounded-xl transition-all hover:scale-105 hover:bg-gray-200 dark:hover:bg-gray-800" 
                    @click="skipQuestion"
                  >
                    Skip Question
                  </UButton>
                </div>
              </div>

              <div v-if="currentQuestion.type === 'recognition'" class="flex flex-col items-center gap-6 py-4">
                <h3 class="text-3xl md:text-4xl font-black text-primary-600 dark:text-primary-400 tracking-widest uppercase bg-primary-50 dark:bg-primary-950/30 px-8 py-4 rounded-xl border border-primary-200 dark:border-primary-800">
                  {{ currentQuestion.targetWord }}
                </h3>

                <div class="w-full aspect-video bg-black rounded-2xl flex flex-col overflow-hidden border-4 border-gray-200 dark:border-gray-700 relative shadow-lg">
                  
                  <div v-if="!isCameraActive" class="flex-1 flex items-center justify-center text-center text-white p-6">
                    <div>
                      <UIcon name="i-lucide-camera-off" class="w-12 h-12 mx-auto mb-3 text-gray-500" />
                      <p class="text-xl font-bold mb-4">The camera is off.</p>
                      <UButton size="md" color="primary" class="px-6 py-3 text-base font-bold rounded-lg shadow" @click="activateCamera">
                        Activate Camera
                      </UButton>
                    </div>
                  </div>

                  <template v-else>
                    <div class="flex-1 w-full relative flex items-center justify-center">
                      <video ref="videoElement" class="absolute inset-0 w-full h-full object-contain transform scale-x-[-1]" autoplay playsinline></video>
                      <canvas ref="canvasElement" class="absolute inset-0 w-full h-full object-contain transform scale-x-[-1] pointer-events-none z-10"></canvas>

                      <div v-if="isPredicting" class="absolute inset-0 z-15 bg-black/50 flex items-center justify-center">
                        <UIcon name="i-lucide-loader-2" class="w-16 h-16 text-primary-500 animate-spin" />
                      </div>
                    </div>

                    <div class="relative bg-gray-900 border-t border-gray-800 z-20 flex flex-col shrink-0">
                      <div class="absolute top-0 left-0 h-1.5 bg-gray-800 w-full">
                        <div class="h-full transition-all duration-75" :class="signFrames.length === maxFrames ? 'bg-green-500' : 'bg-blue-500'" :style="{ width: `${(signFrames.length / maxFrames) * 100}%` }"></div>
                      </div>
                      
                      <div class="flex flex-col sm:flex-row items-center justify-between px-4 py-3 w-full mt-1 gap-3 sm:gap-0">
                        
                        <div class="flex flex-wrap items-center gap-2 sm:gap-3 w-full sm:w-auto justify-center sm:justify-start">
                          
                          <div class="flex items-center text-xs font-mono font-bold mr-1" :class="appState === 'IDLE' ? 'text-yellow-400' : 'text-blue-400'">
                            <div class="w-2 h-2 rounded-full mr-2 animate-pulse" :class="appState === 'IDLE' ? 'bg-yellow-400' : 'bg-blue-400'"></div>
                            <span>{{ appState === 'IDLE' ? 'IDLE' : 'REC' }}</span>
                          </div>

                          <UButton 
                            icon="i-lucide-video" 
                            class="font-bold shadow transition-all text-white"
                            :class="appState === 'IDLE' ? '!bg-green-600 hover:!bg-green-500 hover:scale-105' : '!bg-gray-600 hover:!bg-gray-600 opacity-50 cursor-not-allowed'"
                            :disabled="appState === 'BUFFERING'"
                            @click="startBuffering"
                          >
                            Start <span class="hidden md:inline">[N]</span>
                          </UButton>
                          
                          <UButton 
                            icon="i-lucide-square" 
                            class="font-bold shadow transition-all text-white"
                            :class="appState === 'BUFFERING' ? '!bg-red-600 hover:!bg-red-500 hover:scale-105' : '!bg-gray-600 hover:!bg-gray-600 opacity-50 cursor-not-allowed'"
                            :disabled="appState === 'IDLE'"
                            @click="stopBufferingEarly"
                          >
                            Stop <span class="hidden md:inline">[Space]</span>
                          </UButton>

                          <UButton 
                            :icon="showLandmarks ? 'i-lucide-eye' : 'i-lucide-eye-off'"
                            class="font-bold shadow transition-all text-white hover:scale-105"
                            :class="showLandmarks ? '!bg-green-600 hover:!bg-green-500' : '!bg-gray-600 hover:!bg-gray-500'"
                            @click="showLandmarks = !showLandmarks"
                          >
                            Skeleton: {{ showLandmarks ? 'ON' : 'OFF' }} <span class="hidden md:inline">[L]</span>
                          </UButton>

                          <UButton 
                            color="gray" 
                            variant="ghost" 
                            icon="i-lucide-help-circle" 
                            class="text-gray-400 hover:text-white"
                            @click="isCameraInfoModalOpen = true"
                          />
                        </div>

                        <div class="w-full sm:w-auto flex justify-center sm:justify-end">
                          <UButton 
                            icon="i-lucide-power-off" 
                            class="font-bold shadow-md text-white px-6 py-2 transition-colors !bg-red-600 hover:!bg-red-700"
                            @click="stopCamera"
                          >
                            Exit <span class="hidden md:inline">[Q]</span>
                          </UButton> 
                        </div>

                      </div>
                    </div>
                  </template>
                </div>

                <UButton v-if="!showHint" color="amber" variant="soft" size="md" icon="i-lucide-help-circle" class="font-bold py-2 px-5 mt-2 rounded-xl border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300 shadow-sm transition-all hover:scale-105 hover:bg-amber-100 dark:hover:bg-amber-900/40 hover:shadow-md" @click="showHint = true">
                  Don't remember the sign? Watch the hint
                </UButton>

                <UButton 
                color="gray" 
                variant="soft" 
                size="md" 
                icon="i-lucide-fast-forward" 
                class="font-bold py-2 px-6 rounded-lg transition-all hover:scale-105 hover:bg-gray-200 dark:hover:bg-gray-800" 
                @click="skipQuestion">
                Skip Question
              </UButton>
                
                <transition name="fade">
                <div v-if="showHint" class="mt-6 flex flex-col items-center animate-fade-in w-full">
                  <p class="text-sm font-bold text-amber-500 dark:text-amber-400 mb-3 tracking-wide uppercase flex items-center gap-2">
                    <UIcon name="i-lucide-lightbulb" class="w-4 h-4" /> Reference Sign Animation:
                  </p>
                  <div class="w-full max-w-xl aspect-video rounded-2xl overflow-hidden border-2 border-amber-300 dark:border-amber-700 bg-gray-100 dark:bg-gray-950 p-3 flex items-center justify-center shadow-lg transition-all duration-300">
                    <img 
                      :src="currentQuestion.targetMedia" 
                      alt="ASL Hint Animation" 
                      class="w-full h-full object-contain rounded-xl shadow-inner" 
                    />
                  </div>
                </div>
              </transition>
              </div>

              <template #footer>
                <div class="py-1 text-center text-sm text-gray-400 dark:text-gray-500">
                  DuoSigna Evaluation System
                </div>
              </template>
            </UCard>
          </div>

          <div v-else-if="quizState === 'result'" class="w-full flex flex-col items-center gap-8">
            <UCard class="w-full max-w-xl shadow-xl border-t-8 border-t-primary-500 rounded-3xl">
              <div class="py-10 px-6 text-center">
                <UIcon name="i-lucide-trophy" class="w-24 h-24 text-yellow-500 mx-auto mb-4 drop-shadow-md" />
                <h2 class="text-3xl lg:text-4xl font-black mb-3 text-gray-900 dark:text-white tracking-tight">Quiz Completed!</h2>
                <p class="text-lg text-gray-500 dark:text-gray-400 mb-6">Here is your final report.</p>
                
                <div class="bg-gray-50 dark:bg-gray-800/50 rounded-2xl p-6 mb-8 border border-gray-100 dark:border-gray-800">
                  <p class="text-5xl md:text-6xl font-black text-primary-600 dark:text-primary-400 mb-2">{{ score }} / {{ questions.length }}</p>
                  <p class="text-lg font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wide">Correct Answers</p>
                </div>

                <div class="flex flex-col sm:flex-row justify-center gap-3">
                  <UButton size="lg" color="gray" variant="solid" class="px-6 py-2 text-base font-bold rounded-xl border-2 border-gray-300 dark:border-gray-700 shadow-sm hover:border-primary-500 hover:shadow-lg transition-all" @click="resetQuizToIntro">Back to Quiz</UButton>
                  <UButton size="lg" color="primary" icon="i-lucide-rotate-ccw" class="px-6 py-2 text-base font-bold rounded-xl shadow" @click="startQuiz">Retake Quiz</UButton>
                </div>
              </div>
            </UCard>
          </div>

        </div>
      </div>
    </div>
    <ClientOnly>
      <Teleport to="body">
        <transition name="modal-fade">
          <div v-if="isInfoModalOpen" class="fixed inset-0 z-[995] flex items-center justify-center bg-gray-950/70 backdrop-blur-sm p-4 sm:p-6" @click.self="isInfoModalOpen = false">
            <UCard class="w-full max-w-lg bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-2xl overflow-hidden" :ui="{ divide: 'divide-y divide-gray-100 dark:divide-gray-800', body: 'p-6' }">
              
              <template #header>
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2 text-primary-600 dark:text-primary-400">
                    <UIcon name="i-lucide-info" class="w-6 h-6" />
                    <h3 class="text-xl font-black tracking-wide uppercase text-gray-900 dark:text-white">How to use the Quiz</h3>
                  </div>
                  <UButton color="gray" variant="ghost" icon="i-lucide-x" class="-my-1" @click="isInfoModalOpen = false" />
                </div>
              </template>
              
              <div class="space-y-6 py-2">
                <p class="text-base text-gray-600 dark:text-gray-400 leading-relaxed">
                  Welcome to the <b>DuoSigna Quiz</b>! Test your knowledge and reinforce the signs you've unlocked. Here is how it works:
                </p>

                <div class="space-y-5">
                  <div class="flex gap-4 items-start">
                    <div class="p-2 bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 rounded-xl mt-1">
                      <UIcon name="i-lucide-layers" class="w-6 h-6" />
                    </div>
                    <div>
                      <h4 class="font-bold text-gray-900 dark:text-white text-lg">Choose your Challenge</h4>
                      <p class="text-sm text-gray-500 dark:text-gray-400 leading-relaxed mt-1">
                        Select <b>Mixed</b> to play with the whole dictionary, or choose one or more categories such as <b>Animals</b>, <b>Food & Drinks</b>, or <b>Transport</b>. You will only be tested on signs you have successfully unlocked in the Chatbot!
                      </p>
                    </div>
                  </div>

                  <div class="flex gap-4 items-start">
                    <div class="p-2 bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 rounded-xl mt-1">
                      <UIcon name="i-lucide-shuffle" class="w-6 h-6" />
                    </div>
                    <div>
                      <h4 class="font-bold text-gray-900 dark:text-white text-lg">Multiple Formats</h4>
                      <p class="text-sm text-gray-500 dark:text-gray-400 leading-relaxed mt-1">
                        Answer multiple-choice questions by matching words to signs or signs to words. You have <b>5 attempts</b> for each question.
                      </p>
                    </div>
                  </div>

                  <div class="flex gap-4 items-start">
                    <div class="p-2 bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 rounded-xl mt-1">
                      <UIcon name="i-lucide-camera" class="w-6 h-6" />
                    </div>
                    <div>
                      <h4 class="font-bold text-gray-900 dark:text-white text-lg">Webcam Recognition</h4>
                      <p class="text-sm text-gray-500 dark:text-gray-400 leading-relaxed mt-1">
                        For the ultimate test, the AI will ask you to perform a sign live! Read the correction hints or use "Skip Question" if you get stuck.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <template #footer>
                <div class="flex justify-end">
                  <UButton color="primary" variant="solid" size="md" class="px-6 py-2.5 font-bold rounded-xl shadow-md" @click="isInfoModalOpen = false">
                    Got it!
                  </UButton>
                </div>
              </template>
            </UCard>
          </div>
        </transition>
        <transition name="slide-up">
          <div v-if="feedbackMessage" class="fixed bottom-0 left-0 right-0 z-[999] p-4 md:p-6 flex justify-center pointer-events-none">
            <div class="w-full max-w-xl pointer-events-auto">
              <UAlert
                :color="feedbackType === 'success' ? 'green' : feedbackType === 'info' ? 'blue' : 'red'"
                :icon="feedbackType === 'success' ? 'i-lucide-check-circle' : feedbackType === 'info' ? 'i-lucide-fast-forward' : 'i-lucide-alert-circle'"
                :title="feedbackMessage"
                variant="solid" 
                class="w-full text-base md:text-lg py-4 px-6 rounded-2xl border-t-4 shadow-2xl text-center"
                :class="[
                  feedbackType === 'success' ? 'border-green-700 bg-green-600/95 backdrop-blur-md' : 
                  feedbackType === 'info' ? 'border-blue-700 bg-blue-600/95 backdrop-blur-md' : 
                  'border-red-700 bg-red-600/95 backdrop-blur-md'
                ]"
                :ui="{ 
                  title: 'text-lg md:text-xl font-bold text-center w-full block tracking-wide text-white', 
                  icon: { base: 'w-6 h-6 text-white' } 
                }"
              >
                <template #description v-if="feedbackType === 'error' && feedbackHints.length > 0">
                  <div class="mt-3 text-left text-xs md:text-sm bg-black/20 p-3 rounded-xl border border-white/10 max-w-md mx-auto">
                    <p class="font-extrabold text-white mb-1.5 uppercase tracking-wider flex items-center gap-1.5">
                      <UIcon name="i-lucide-lightbulb" class="w-4 h-4 text-yellow-300" /> Correction Hints:
                    </p>
                    <ul class="list-disc list-inside space-y-1 text-gray-100">
                      <li v-for="(hint, i) in feedbackHints" :key="i">
                        {{ hint.message }}
                      </li>
                    </ul>
                  </div>
                </template>
              </UAlert>
            </div>
          </div>
        </transition>
        <transition name="info-fade">
          <div v-if="isCameraInfoModalOpen" class="fixed inset-0 z-[996] flex items-center justify-center bg-gray-950/70 backdrop-blur-sm p-4 sm:p-6" @click.self="isCameraInfoModalOpen = false">
            <UCard class="w-full max-w-md bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-2xl overflow-hidden" :ui="{ divide: 'divide-y divide-gray-100 dark:divide-gray-800', body: 'p-6' }">
              <template #header>
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2 text-primary-600 dark:text-primary-400">
                    <UIcon name="i-lucide-video" class="w-6 h-6" />
                    <h3 class="text-xl font-black tracking-wide uppercase text-gray-900 dark:text-white">Recording Guide</h3>
                  </div>
                  <UButton color="gray" variant="ghost" icon="i-lucide-x" class="-my-1" @click="isCameraInfoModalOpen = false" />
                </div>
              </template>
              
              <div class="space-y-4 py-2 text-gray-900 dark:text-gray-300 text-sm leading-relaxed">
                <p>
                  To get the best results from the <b>Sign Recognition</b>, here is how you should record your sign:
                </p>
                <ul class="list-disc list-inside space-y-3 mt-4">
                  <li>Click <b>Start</b> (or press [N]) to begin capturing your movement.</li>
                  <li><b class="text-gray-900 dark:text-white">Continuous Mode:</b> You can repeat the sign continuously until the buffer progress bar reaches the end. The Sign Tutor will analyze the whole sequence.</li>
                  <li><b class="text-gray-900 dark:text-white">Single Mode:</b> If you prefer to perform the sign just once, do it clearly and immediately click <b>Stop</b> (or press Spacebar) to let the Sign Tutor evaluate your recording early.</li>
                </ul>
                <div class="mt-4 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg text-amber-700 dark:text-amber-400 font-medium text-xs">
                  <UIcon name="i-lucide-alert-triangle" class="inline w-4 h-4 mr-1 align-text-bottom" /> Make sure your hands and face are clearly visible!
                </div>
              </div>

              <template #footer>
                <div class="flex justify-end">
                  <UButton color="primary" variant="solid" size="md" class="px-6 py-2.5 font-bold rounded-xl shadow-md" @click="isCameraInfoModalOpen = false">Understood</UButton>
                </div>
              </template>
            </UCard>
          </div>
        </transition>
      </Teleport>
    </ClientOnly>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

/* Transizione Slide-Up per il Popup in sovraimpressione */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275), opacity 0.3s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

/* Transizione per il modale info */
.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity 0.3s ease; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }

</style>
