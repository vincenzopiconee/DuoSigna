<script setup>
import { ref, nextTick, computed, onBeforeUnmount, onMounted } from 'vue'

const { token } = useAuth()

// ==============================================
// CHATBOT STATE & LOGIC
// ==============================================
const searchQuery = ref('')
const isLoading = ref(false)
const chatContainer = ref(null)

const messages = useState('chat-messages', () => []) 
const chatId = useState('chat-id', () => null) 
const pendingLearningSign = useState('pending-learning-sign', () => null)

const chatList = ref([])
const isDeleteChatModalOpen = ref(false)
const chatToDelete = ref(null)

const fetchChatHistoryList = async () => {
  try {
    const response = await $fetch('http://127.0.0.1:8000/chats', {
      headers: { 'Authorization': token.value }
    })
    chatList.value = response 
  } catch (error) {
    console.error("Errore nel recupero della lista chat:", error)
  }
}

const startNewChat = () => {
  messages.value = []
  chatId.value = null
}

const loadChat = async (selectedChatId) => {
  chatId.value = selectedChatId
  isLoading.value = true
  
  try {
    const response = await $fetch(`http://127.0.0.1:8000/chat/${selectedChatId}`, {
      headers: { 'Authorization': token.value }
    })
    messages.value = response.messages
      .filter(msg => msg.role !== 'system')
      .map(msg => ({
        role: msg.role,
        content: msg.content,
        purpose: msg.purpose,
        target_word: msg.target_word,
        level: msg.level,
        video_link_or_gif: msg.video_link_or_gif 
      }))
    
  } catch (error) {
    console.error("Error loading chat:", error)
  } finally {
    isLoading.value = false
    scrollToBottom()
  }
}

// Apre semplicemente la modale e si "segna" quale chat eliminare
const deleteChat = (idToDelete) => {
  chatToDelete.value = idToDelete
  isDeleteChatModalOpen.value = true
}

// Esegue l'eliminazione vera e propria quando l'utente clicca "Yes"
const confirmDeleteChat = async () => {
  if (!chatToDelete.value) return
  
  const idToDelete = chatToDelete.value
  isDeleteChatModalOpen.value = false // Chiude la modale

  try {
    // Chiamata DELETE al backend
    await $fetch(`http://127.0.0.1:8000/chat/${idToDelete}`, {
      method: 'DELETE',
      headers: { 'Authorization': token.value }
    })

    // Rimuoviamo la chat eliminata dalla lista
    chatList.value = chatList.value.filter(chat => chat.id !== idToDelete)

    // Se l'utente stava guardando proprio questa chat, resettiamo la vista
    if (chatId.value === idToDelete) {
      startNewChat()
    }
    
  } catch (error) {
    console.error("Error deleting chat:", error)
    // Mostriamo un piccolo alert di fallback solo se il server va in crash
    alert("There was an error deleting the chat. Please try again.") 
  } finally {
    chatToDelete.value = null // Pulizia
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

const sendMessage = async (messageText = null) => {
  const userText = (typeof messageText === 'string' ? messageText : searchQuery.value).trim()
  if (!userText || isLoading.value) return

  searchQuery.value = ''
  messages.value.push({ role: 'user', content: userText })
  scrollToBottom()
  
  isLoading.value = true

  try {
    const response = await $fetch('http://127.0.0.1:8000/chat', {
      method: 'POST',
      headers: { 'Authorization': token.value },
      body: { question: userText, chat_id: chatId.value }
    })

    if (!chatId.value && response.chat_id) {
      chatId.value = response.chat_id
      await fetchChatHistoryList()
    }

    messages.value.push({
      role: 'assistant',
      content: response.answer,
      purpose: response.purpose,
      target_word: response.target_word,
      level: response.level,
      video_link_or_gif: response.video_link_or_gif 
    })

  } catch (error) {
    console.error("Server connection error:", error)
    messages.value.push({
      role: 'assistant',
      content: "Sorry, there was a connection error with the server. Please check if the backend is running!",
      isError: true
    })
  } finally {
    isLoading.value = false
    scrollToBottom()
  }
}

onMounted(async () => {
  await fetchChatHistoryList()

  const signToLearn = pendingLearningSign.value
  if (!signToLearn) return

  pendingLearningSign.value = null
  startNewChat()
  await sendMessage(`How do I sign "${signToLearn}"?`)
})

// ==============================================
// FUNZIONI DI UTILITÀ MULTIMEDIALE
// ==============================================
const isYouTube = (url) => {
  if (!url) return false
  return url.includes('youtube.com') || url.includes('youtu.be')
}

const getYouTubeEmbedUrl = (url) => {
  if (!url) return ''
  let videoId = ''
  if (url.includes('youtu.be/')) {
    videoId = url.split('youtu.be/')[1].split('?')[0]
  } else if (url.includes('v=')) {
    videoId = url.split('v=')[1].split('&')[0]
  } else if (url.includes('embed/')) {
    videoId = url.split('embed/')[1].split('?')[0]
  }
  return `https://www.youtube.com/embed/${videoId}`
}

const getMediaUrl = (url) => {
  if (!url) return ''
  if (url.startsWith('http')) return url
  if (url.startsWith('/')) return `http://127.0.0.1:8000${url}`
  return `http://127.0.0.1:8000/${url}`
}

// ==============================================
// WEBCAM & MEDIAPIPE LOGIC (HUD & SKELETON)
// ==============================================
const isCameraModalOpen = ref(false)
const isInfoModalOpen = ref(false)
const isCameraInfoModalOpen = ref(false)

const cameraError = ref(false)

const videoElement = ref(null)
const canvasElement = ref(null)
const canvasCtx = ref(null)

const isPredicting = ref(false)
const appState = ref('IDLE') 
const showLandmarks = ref(true)

const recognizedWord = ref('Waiting...')
const confidenceScore = ref(0)
const isPredictionCorrect = ref(null)
const feedbackHints = ref([]) 

const showSuccessAlert = ref(false)
const showWarningAlert = ref(false)
let alertTimeout = null
let warningTimeout = null

const triggerSuccessAlert = () => {
  showWarningAlert.value = false 
  showSuccessAlert.value = true
  if (alertTimeout) clearTimeout(alertTimeout)
  alertTimeout = setTimeout(() => {
    showSuccessAlert.value = false
  }, 4000)
}

const triggerWarningAlert = () => {
  showSuccessAlert.value = false 
  showWarningAlert.value = true
  if (warningTimeout) clearTimeout(warningTimeout)
  warningTimeout = setTimeout(() => {
    showWarningAlert.value = false
  }, 4000)
}

// --- ESTRAZIONE DATI PER LA DASHBOARD CAMERA ---
const activeLearningMessage = computed(() => {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    const msg = messages.value[i]
    if (msg.role === 'assistant' && msg.target_word && msg.target_word.toLowerCase() !== 'null') {
      return msg
    }
  }
  return null
})

const currentTargetWord = computed(() => activeLearningMessage.value?.target_word || 'Unknown')
const currentLevel = computed(() => activeLearningMessage.value?.level || 'level_0')
const currentInstructions = computed(() => activeLearningMessage.value?.content || 'Nessuna istruzione trovata.')
const currentMedia = computed(() => activeLearningMessage.value?.video_link_or_gif || null)

const maxFrames = computed(() => currentLevel.value === 'level_1' ? 150 : 384)

let holistic = null
let camera = null
let drawingUtils = null
let mpHolistic = null
const signFrames = ref([])
const MIN_FRAMES = 15

const handleCameraAction = () => {
  if (currentLevel.value === 'level_2' || currentLevel.value === 'level_1') {
    activateCamera()
  }
}

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
      submitSign(true) 
    }
  }
}

const activateCamera = async () => {
  // Togliamo il focus dalla barra di testo
  if (document.activeElement && document.activeElement.blur) {
    document.activeElement.blur()
  }

  isCameraModalOpen.value = true
  appState.value = 'IDLE'
  signFrames.value = []
  recognizedWord.value = 'Waiting...'
  confidenceScore.value = 0
  isPredictionCorrect.value = null
  feedbackHints.value = [] 
  showSuccessAlert.value = false 
  showWarningAlert.value = false
  cameraError.value = false // <-- Resettiamo l'errore ad ogni avvio
  
  // --- NUOVO BLOCCO CONTROLLO PERMESSI ---
  try {
    // Chiediamo esplicitamente l'accesso. Se l'utente clicca "Blocca", questo throwerà un errore.
    const stream = await navigator.mediaDevices.getUserMedia({ video: true })
    // Se ha accettato, chiudiamo subito lo stream di test. MediaPipe aprirà il suo in modo pulito.
    stream.getTracks().forEach(track => track.stop())
  } catch (err) {
    console.error("Accesso alla fotocamera negato o non disponibile:", err)
    cameraError.value = true // Attiviamo la schermata di errore
    return // Blocchiamo l'avvio di MediaPipe
  }
  // ---------------------------------------

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
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        refineFaceLandmarks: false,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      })

      holistic.onResults(onResults)

      camera = new Camera(videoElement.value, {
        onFrame: async () => {
          if (isCameraModalOpen.value && videoElement.value) {
            if (canvasElement.value && canvasElement.value.width !== videoElement.value.videoWidth) {
              canvasElement.value.width = videoElement.value.videoWidth
              canvasElement.value.height = videoElement.value.videoHeight
            }
            await holistic.send({ image: videoElement.value })
          }
        },
        width: 1280,
        height: 720
      })

      camera.start()
      window.addEventListener('keydown', handleKeyboard)
    } catch (err) {
      console.error("Error loading MediaPipe:", err)
    }
  }
}

// Aggiungi questa riga sotto a isInfoModalOpen
const isMediaZoomOpen = ref(false)

const stopCamera = () => {
  isCameraModalOpen.value = false
  isMediaZoomOpen.value = false // <- Chiudiamo anche lo zoom per sicurezza
  window.removeEventListener('keydown', handleKeyboard)
  if (camera) { camera.stop(); camera = null }
  if (holistic) { holistic.close(); holistic = null }
  stopAudio()
}

const startBuffering = () => {
  signFrames.value = []
  feedbackHints.value = [] 
  showSuccessAlert.value = false
  showWarningAlert.value = false
  
  recognizedWord.value = 'Waiting...'
  confidenceScore.value = 0
  isPredictionCorrect.value = null
  
  appState.value = 'BUFFERING'
}

const stopBufferingEarly = () => {
  if (appState.value === 'BUFFERING') {
    if (signFrames.value.length >= MIN_FRAMES) {
      submitSign(true)
    } else {
      // Se l'utente clicca stop quasi istantaneamente, resettiamo il buffer
      appState.value = 'IDLE'
      signFrames.value = []
    }
  }
}

const submitSign = async (returnToIdle = true) => {
  if (signFrames.value.length < MIN_FRAMES) return

  isPredicting.value = true
  const framesToSend = [...signFrames.value] 
  signFrames.value = [] 

  const isLevel1 = currentLevel.value === 'level_1'
  const targetUrl = isLevel1 
    ? 'http://127.0.0.1:8000/recognize-letter' 
    : 'http://127.0.0.1:8000/recognize-sign'

  try {
    const response = await $fetch(targetUrl, {
      method: 'POST',
      headers: { 'Authorization': token.value },
      body: { 
        frames: framesToSend, 
        target_word: currentTargetWord.value
      }
    })
    
    recognizedWord.value = response.predicted_word
    confidenceScore.value = Math.round(response.confidence * 100)
    isPredictionCorrect.value = response.is_correct
    
    if (response.is_correct) {
      triggerSuccessAlert()
    } else {
      triggerWarningAlert()
    }

    if (response.feedback) {
      feedbackHints.value = response.feedback
    } else {
      feedbackHints.value = []
    }

    if (returnToIdle) appState.value = 'IDLE'

  } catch (error) {
    console.error("Inference error:", error)
    recognizedWord.value = "Error"
    if (returnToIdle) appState.value = 'IDLE'
  } finally {
    isPredicting.value = false
  }
}

const handleKeyboard = (e) => {
  if (!isCameraModalOpen.value) return

  // NUOVO: Se lo zoom è aperto, blocchiamo i comandi della telecamera
  if (isMediaZoomOpen.value) {
    if (e.key === 'Escape' || e.key.toLowerCase() === 'q') {
      e.preventDefault()
      isMediaZoomOpen.value = false
    }
    return 
  }


  const key = e.key.toLowerCase()

  if (key === 'n' && appState.value === 'IDLE') {
    e.preventDefault() // <-- Aggiunto per bloccare la digitazione
    startBuffering()
  } else if (key === ' ' && appState.value === 'BUFFERING') {
    e.preventDefault() 
    if (signFrames.value.length >= MIN_FRAMES) submitSign(true)
  } else if (key === 'l') {
    e.preventDefault() // <-- Aggiunto per bloccare la digitazione
    showLandmarks.value = !showLandmarks.value
  } else if (key === 'q') {
    e.preventDefault() // <-- Aggiunto per bloccare la digitazione
    stopCamera()
  }
}

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyboard)
  stopCamera()
})

// Stato per capire quale messaggio sta riproducendo attualmente l'audio (per mostrare un loader)
const isPlayingAudioFor = ref(null)
const currentAudio = ref(null)      
const isAudioLoading = ref(false)

const stopAudio = () => {
  if (currentAudio.value) {
    currentAudio.value.pause()
    currentAudio.value.currentTime = 0 // Riporta all'inizio
    if (currentAudio.value.src) {
      window.URL.revokeObjectURL(currentAudio.value.src) // Pulisce la memoria del browser
    }
    currentAudio.value = null
  }
  isPlayingAudioFor.value = null
  isAudioLoading.value = false
}

const toggleAudio = async (text, index) => {
  // Se clicco sul messaggio che sta già suonando (o caricando), lo fermo
  if (isPlayingAudioFor.value === index) {
    stopAudio()
    return
  }

  // Se stava suonando un ALTRO messaggio, lo fermo prima di far partire il nuovo
  if (currentAudio.value) {
    stopAudio()
  }

  isPlayingAudioFor.value = index
  isAudioLoading.value = true

  try {
    const response = await $fetch('http://127.0.0.1:8000/synthesize-audio', {
      method: 'POST',
      headers: { 'Authorization': token.value },
      body: { text: text },
      responseType: 'blob'
    })

    if (isPlayingAudioFor.value !== index) {
      return
    }

    const audioUrl = window.URL.createObjectURL(response)
    const audio = new Audio(audioUrl)
    currentAudio.value = audio

    // Quando finisce da solo, pulisci
    audio.onended = () => {
      stopAudio()
    }

    isAudioLoading.value = false
    await audio.play()

  } catch (error) {
    console.error("Error in audio playback:", error)
    stopAudio()
  }
}

onBeforeUnmount(() => {
  stopAudio()
})


</script>



<template>
  <div>
    <div class="flex min-h-[calc(100vh-140px)] bg-gray-50 dark:bg-transparent transition-colors duration-200 w-full">
      
      <AppSidebar />

      <div class="flex-1 px-4 lg:px-8 py-8 w-full flex justify-center items-start">
        <div class="max-w-4xl w-full flex flex-col gap-6 min-h-[calc(100vh-180px)] pb-8">
          
          <div class="flex items-center justify-between bg-white dark:bg-gray-900 p-4 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800">
            <div class="flex items-center gap-4">
              <div class="p-3 bg-primary-100 dark:bg-primary-900/50 rounded-xl">
                <UIcon name="i-lucide-bot" class="w-8 h-8 text-primary-600 dark:text-primary-400" />
              </div>
              <div>
                <div class="flex items-center gap-2">
                  <h1 class="text-2xl font-extrabold text-gray-900 dark:text-white tracking-tight">Sign Tutor</h1>
                  <UButton icon="i-lucide-info" color="primary" variant="ghost" size="xs" class="rounded-full hover:scale-110 transition-transform" @click="isInfoModalOpen = true" />
                </div>
                <p class="text-sm text-gray-500 dark:text-gray-300">Ask me how to sign a word or ask a question about ASL grammar.</p>
              </div>
            </div>
          </div>

          <div class="flex-1 bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 overflow-hidden flex flex-col relative">
            <div ref="chatContainer" class="flex-1 overflow-y-auto p-6 scroll-smooth" :class="messages.length === 0 ? 'flex flex-col items-center justify-center' : 'space-y-6'">
              
              <div v-if="messages.length === 0" class="flex flex-col items-center justify-center text-center opacity-80 mt-6">
                <UIcon name="i-lucide-messages-square" class="w-20 h-20 mb-4 text-gray-400 dark:text-gray-500" />
                <p class="text-lg font-bold text-gray-600 dark:text-gray-200">The chat is empty.</p>
                <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Type "How do you sign Airplane?" to start.</p>
              </div>

              <div v-for="(msg, index) in messages" :key="index" :class="msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'">
                <div v-if="msg.role === 'user'" class="bg-primary-600 text-white px-6 py-3 rounded-2xl rounded-tr-none max-w-[80%] shadow-md">
                  <p class="text-base">{{ msg.content }}</p>
                </div>

                <div v-else class="bg-gray-100 dark:bg-gray-800/90 border border-gray-200 dark:border-gray-600 px-6 py-4 rounded-2xl rounded-tl-none max-w-[85%] shadow-sm group relative">
                  
                  <div class="flex items-center gap-3 mb-3">
                    <UBadge 
                      v-if="msg.purpose === 'translation' && msg.target_word && msg.target_word.toLowerCase() !== 'null'" 
                      color="primary" 
                      variant="soft" 
                      size="md" 
                      class="font-black uppercase tracking-widest shadow-sm dark:bg-primary-900/60 dark:text-primary-300"
                    >
                      Target: {{ msg.target_word }}
                    </UBadge>

                    <UButton
                      v-if="isPlayingAudioFor !== index"
                      icon="i-lucide-volume-2"
                      color="primary"
                      variant="soft"
                      size="sm"
                      class="rounded-lg font-bold shadow-sm transition-all hover:scale-105 dark:bg-primary-900/50 dark:text-primary-300 dark:hover:bg-primary-900/80"
                      :disabled="isPlayingAudioFor !== null"
                      @click="toggleAudio(msg.content, index)"
                    >
                      Listen
                    </UButton>

                    <UButton
                      v-else
                      icon="i-lucide-square"
                      color="red"
                      variant="soft"
                      size="sm"
                      class="rounded-lg font-bold shadow-sm transition-all hover:scale-105 dark:bg-red-900/50 dark:text-red-300"
                      :loading="isAudioLoading"
                      @click="toggleAudio(msg.content, index)"
                    >
                      Stop
                    </UButton>
                  </div>

                  <p class="text-base text-gray-800 dark:text-gray-100 leading-relaxed whitespace-pre-wrap">{{ msg.content }}</p>
                  
                  <div v-if="msg.video_link_or_gif && msg.video_link_or_gif !== 'null'" class="mt-4 rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 shadow-sm max-w-md">
                    <div v-if="isYouTube(msg.video_link_or_gif)" class="relative w-full aspect-video bg-black rounded-xl overflow-hidden">
                      <iframe 
                        :src="getYouTubeEmbedUrl(msg.video_link_or_gif)" 
                        class="absolute inset-0 w-full h-full"
                        frameborder="0" 
                        allowfullscreen>
                      </iframe>
                    </div>
                    <div v-else class="w-full aspect-square sm:aspect-video bg-gray-100 dark:bg-gray-950 rounded-xl p-2 flex items-center justify-center overflow-hidden border border-gray-200 dark:border-gray-800">
                      <img :src="getMediaUrl(msg.video_link_or_gif)" alt="ASL Sign Animation" class="w-full h-full object-contain rounded-lg shadow-inner" />
                    </div>
                  </div>
                  
                </div>
              </div>

              <div v-if="isLoading" class="flex justify-start">
                <div class="bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-6 py-4 rounded-2xl rounded-tl-none flex items-center gap-3">
                  <UIcon name="i-lucide-loader-2" class="w-5 h-5 animate-spin text-primary-500" />
                  <span class="text-sm font-medium text-gray-500 dark:text-gray-400">The tutor is analyzing...</span>
                </div>
              </div>
            </div>

            <div id="tour-chat-input" class="p-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
              <form @submit.prevent="sendMessage" class="flex gap-3">
                <UInput 
                  v-model="searchQuery" 
                  placeholder="Type your question here..." 
                  size="xl" 
                  class="flex-1" 
                  :disabled="isLoading" 
                  autocomplete="off" 
                  :ui="{ 
                    rounded: 'rounded-xl', 
                    color: { white: { outline: 'bg-white dark:bg-gray-800 ring-gray-300 dark:ring-gray-600 text-gray-900 dark:text-white' } } 
                  }" 
                />
                
                <UButton 
                  type="submit" 
                  color="primary" 
                  size="xl" 
                  icon="i-lucide-send" 
                  :loading="isLoading" 
                  :disabled="!searchQuery" 
                  class="px-8 rounded-xl font-bold shadow-md hover:scale-105 transition-transform dark:bg-primary-500 dark:text-white dark:hover:bg-primary-400 disabled:opacity-50 dark:disabled:bg-gray-800 dark:disabled:text-gray-500"
                >
                  Send
                </UButton>
              </form>
            </div>
          </div>

          <transition name="fade">
            <UCard v-if="currentLevel === 'level_1' || currentLevel === 'level_2'" class="w-full shadow-lg border border-primary-200 dark:border-primary-800 bg-primary-50 dark:bg-primary-900/10">
              <div class="flex flex-col sm:flex-row items-center justify-between gap-6 text-center sm:text-left">
                <div class="flex flex-col sm:flex-row items-center gap-4">
                  <div class="p-4 bg-white dark:bg-gray-800 rounded-full shadow-sm">
                    <UIcon name="i-lucide-camera" class="w-8 h-8 text-primary-600 dark:text-primary-400" />
                  </div>
                  <div>
                    <h4 class="font-bold text-lg text-gray-900 dark:text-white mb-1">Do you want to check if you learned <span class="text-primary-600 dark:text-primary-400 uppercase">"{{ currentTargetWord }}"</span> correctly?</h4>
                    <p class="text-sm text-gray-600 dark:text-gray-400">Activate the camera, repeat the sign, and get real-time feedback.</p>
                  </div>
                </div>
                <UButton size="lg" color="primary" @click="handleCameraAction" class="whitespace-nowrap px-8 py-3 rounded-xl shadow font-bold">
                  Activate Camera
                </UButton>
              </div>
            </UCard>
          </transition>

        </div>
      </div>

      <ChatHistorySidebar 
        :chats="chatList"
        :currentChatId="chatId"
        @new-chat="startNewChat"
        @select-chat="loadChat"
        @delete-chat="deleteChat"
      />

    </div>

    <ClientOnly>
      <Teleport to="body">
        
        <transition name="camera-fade">
          <div v-if="isCameraModalOpen" class="fixed inset-0 z-[990] flex p-4 sm:p-6 lg:p-8 gap-4 sm:gap-6 bg-gray-950/95 backdrop-blur-md">
            
            <div class="w-[30%] h-full bg-gray-900 rounded-2xl border border-gray-700 shadow-2xl flex flex-col overflow-hidden hidden md:flex">
              <div class="p-6 flex-1 overflow-y-auto space-y-8 no-scrollbar">
                
                <div>
                  <UBadge color="primary" variant="soft" class="mb-3 font-bold">Target Sign</UBadge>
                  <h3 class="text-3xl font-black text-white uppercase tracking-wider drop-shadow-sm">{{ currentTargetWord }}</h3>
                </div>

                <div>
                  <div class="flex items-center justify-between mb-3">
                    <h4 class="text-xs font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2">
                      <UIcon name="i-lucide-book-open" class="w-4 h-4" /> Instructions
                    </h4>
                    <div>
                      <UButton
                        v-if="isPlayingAudioFor !== 'modal'"
                        icon="i-lucide-volume-2"
                        size="xs"
                        class="bg-white dark:bg-white text-gray-900 dark:text-gray-900 hover:bg-gray-100 dark:hover:bg-gray-100 rounded-lg font-bold shadow-sm transition-all hover:scale-105"
                        :disabled="isPlayingAudioFor !== null"
                        @click="toggleAudio(currentInstructions, 'modal')"
                      >
                        Listen
                      </UButton>
                      <UButton
                        v-else
                        icon="i-lucide-square"
                        color="red"
                        variant="solid"
                        size="xs"
                        class="bg-white dark:bg-white text-gray-900 dark:text-gray-900 hover:bg-gray-100 dark:hover:bg-gray-100 rounded-lg font-bold shadow-sm transition-all hover:scale-105"
                        :loading="isAudioLoading"
                        @click="toggleAudio(currentInstructions, 'modal')"
                      >
                        Stop
                      </UButton>
                    </div>
                  </div>
                  <p class="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">{{ currentInstructions }}</p>
                </div>

                <div v-if="currentMedia && currentMedia !== 'null'">
                  <h4 class="text-xs font-bold text-gray-400 mb-3 uppercase tracking-widest flex items-center gap-2">
                    <UIcon name="i-lucide-video" class="w-4 h-4" /> Reference
                  </h4>
                  <div 
                    class="relative w-full rounded-xl overflow-hidden border border-gray-700 shadow-sm cursor-pointer group"
                    @click="isMediaZoomOpen = true"
                  >
                    <div class="pointer-events-none">
                      <div v-if="isYouTube(currentMedia)" class="relative w-full aspect-video bg-black">
                        <iframe :src="getYouTubeEmbedUrl(currentMedia)" class="absolute inset-0 w-full h-full" frameborder="0" allowfullscreen></iframe>
                      </div>
                      <div v-else class="w-full aspect-square sm:aspect-video bg-gray-100 dark:bg-gray-950 p-2 flex items-center justify-center">
                        <img :src="getMediaUrl(currentMedia)" alt="ASL Sign Animation" class="w-full h-full object-contain rounded-lg shadow-inner" />
                      </div>
                    </div>
                    <div class="absolute inset-0 bg-black/50 backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex flex-col items-center justify-center z-10">
                      <UIcon name="i-lucide-zoom-in" class="w-10 h-10 text-white drop-shadow-lg mb-2" />
                      <span class="text-white font-bold tracking-wide text-sm">Click to Zoom</span>
                    </div>
                  </div>
                </div>

              </div>
            </div>

            <div class="flex-1 h-full bg-gray-900 rounded-2xl overflow-hidden shadow-2xl border border-gray-700 relative flex flex-col">
              
              <div class="relative z-20 h-16 bg-gradient-to-b from-black/80 to-transparent flex items-center px-6">
                <h2 class="text-2xl font-black uppercase tracking-widest drop-shadow-md" :class="isPredictionCorrect ? 'text-green-400' : 'text-cyan-400'">
                  Sign: {{ recognizedWord }} &nbsp;&nbsp; {{ confidenceScore }}%
                </h2>
                <div class="ml-auto text-white/70 text-sm font-medium">
                  <UBadge color="gray" variant="soft" class="ml-2">{{ currentLevel }}</UBadge>
                </div>
              </div>

              <transition name="slide-down">
                <div v-if="showSuccessAlert" class="absolute top-16 left-0 right-0 z-30 flex justify-center mt-4 pointer-events-none">
                  <div class="bg-green-500/90 backdrop-blur-md text-white px-6 py-3 rounded-full shadow-2xl flex items-center gap-3 border border-green-400">
                    <UIcon name="i-lucide-check-circle-2" class="w-6 h-6 animate-bounce" />
                    <span class="font-bold tracking-wide">Excellent! Sign learned and saved to your dictionary.</span>
                  </div>
                </div>
              </transition>

              <transition name="slide-down">
                <div v-if="showWarningAlert" class="absolute top-16 left-0 right-0 z-30 flex justify-center mt-4 pointer-events-none">
                  <div class="bg-amber-500/90 backdrop-blur-md text-white px-6 py-3 rounded-full shadow-2xl flex items-center gap-3 border border-amber-400">
                    <UIcon name="i-lucide-alert-circle" class="w-6 h-6 animate-pulse" />
                    <span class="font-bold tracking-wide">Not quite 65%! Check the instructions on the left to improve.</span>
                  </div>
                </div>
              </transition>

              <div class="flex-1 w-full bg-black flex items-center justify-center relative overflow-hidden">
                
                <div v-if="cameraError" class="absolute inset-0 z-20 flex flex-col items-center justify-center bg-gray-900 p-6 text-center border-4 border-dashed border-gray-700 m-4 rounded-xl">
                  <div class="p-4 bg-red-500/10 rounded-full mb-4">
                    <UIcon name="i-lucide-camera-off" class="w-12 h-12 text-red-500" />
                  </div>
                  <h3 class="text-2xl font-black text-white mb-2 tracking-wide uppercase">Camera Access Blocked</h3>
                  <p class="text-gray-400 max-w-md leading-relaxed text-sm">
                    We cannot evaluate your signs because camera access has been denied or no video device was found.
                    <br><br>
                    To fix this, please enable camera permissions for this website in your browser settings and refresh the page.
                  </p>
                  <UButton color="primary" variant="solid" size="lg" icon="i-lucide-refresh-cw" class="mt-8 font-bold px-8 rounded-xl shadow-lg" @click="activateCamera">
                    Check Again
                  </UButton>
                </div>

                <template v-else>
                  <video ref="videoElement" class="absolute inset-0 w-full h-full object-contain transform scale-x-[-1]" autoplay playsinline></video>
                  <canvas ref="canvasElement" class="absolute inset-0 w-full h-full object-contain transform scale-x-[-1] pointer-events-none z-10"></canvas>
                  <div v-if="isPredicting" class="absolute inset-0 z-15 bg-black/40 flex items-center justify-center">
                    <UIcon name="i-lucide-loader-2" class="w-16 h-16 text-primary-500 animate-spin" />
                  </div>
                </template>

              </div>

              <div v-if="currentLevel === 'level_1' && feedbackHints.length > 0 && appState === 'IDLE'" class="bg-gray-800 p-4 border-t border-yellow-500/40 max-h-48 overflow-y-auto">
                <h4 class="text-yellow-400 font-bold mb-2 flex items-center gap-2 text-sm tracking-wide uppercase"><UIcon name="i-lucide-lightbulb" class="w-4 h-4" /> Suggerimenti di Correzione:</h4>
                <ul class="space-y-1">
                  <li v-for="(hint, i) in feedbackHints" :key="i" class="text-sm text-gray-200 flex items-start gap-2 bg-gray-900/40 p-2 rounded-lg border border-gray-700/50">
                    <span class="text-yellow-500 font-bold mt-0.5">•</span><span>{{ hint.message }}</span>
                  </li>
                </ul>
              </div>

              <div class="relative bg-gray-900 border-t border-gray-800 z-20 flex flex-col shrink-0">
                <div class="absolute top-0 left-0 h-1.5 bg-gray-800 w-full">
                  <div class="h-full transition-all duration-75" :class="signFrames.length === maxFrames ? 'bg-green-500' : 'bg-blue-500'" :style="{ width: `${(signFrames.length / maxFrames) * 100}%` }"></div>
                </div>
                
                <div class="flex flex-col sm:flex-row items-center justify-between px-4 py-3 w-full mt-1 gap-3 sm:gap-0">
                  
                  <div class="flex flex-wrap items-center gap-2 sm:gap-4 w-full sm:w-auto justify-center sm:justify-start">
                    
                    <div class="flex items-center text-xs font-mono font-bold mr-1" :class="appState === 'IDLE' ? 'text-yellow-400' : 'text-green-400'">
                       <div class="w-2 h-2 rounded-full mr-2 animate-pulse" :class="appState === 'IDLE' ? 'bg-yellow-400' : 'bg-green-400'"></div>
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
                      icon="i-lucide-log-out" 
                      class="font-bold shadow-md text-white px-6 py-2 transition-colors !bg-red-600 hover:!bg-red-700"
                      @click="stopCamera"
                    >
                      Exit <span class="hidden md:inline">[Q]</span>
                    </UButton>
                  </div>

                </div>
              </div>

            </div>
          </div>
        </transition>

        <transition name="zoom-fade">
          <div v-if="isMediaZoomOpen" class="fixed inset-0 z-[999] flex items-center justify-center bg-black/90 backdrop-blur-xl p-4 sm:p-8" @click.self="isMediaZoomOpen = false">
            <div class="relative w-full max-w-5xl aspect-video bg-gray-900 rounded-2xl border border-gray-700 shadow-2xl flex items-center justify-center overflow-hidden">
              <UButton color="gray" variant="ghost" icon="i-lucide-x" size="xl" class="absolute top-4 right-4 z-50 text-white bg-black/50 hover:bg-black/80 rounded-full" @click="isMediaZoomOpen = false" />
              <iframe v-if="isYouTube(currentMedia)" :src="getYouTubeEmbedUrl(currentMedia)" class="w-full h-full" frameborder="0" allowfullscreen></iframe>
              <img v-else :src="getMediaUrl(currentMedia)" alt="Zoomed Sign Animation" class="w-full h-full object-contain p-4" />
            </div>
            <p class="absolute bottom-6 text-gray-400 font-medium tracking-wide pointer-events-none">Click anywhere outside or press <kbd class="px-2 py-1 bg-gray-800 rounded mx-1 text-white">Esc</kbd> to close</p>
          </div>
        </transition>

        <transition name="modal-fade">
          <div v-if="isDeleteChatModalOpen" class="fixed inset-0 z-[999] flex items-center justify-center bg-gray-900/60 backdrop-blur-sm p-4" @click.self="isDeleteChatModalOpen = false">
            <UCard class="w-full max-w-md shadow-2xl relative border-t-4 border-t-red-500">
              <template #header>
                <div class="flex items-center gap-2 text-red-500">
                  <UIcon name="i-lucide-alert-triangle" class="w-6 h-6" />
                  <h3 class="text-xl font-bold">Delete Chat</h3>
                </div>
              </template>
              <div class="py-4">
                <p class="text-gray-600 dark:text-gray-300 font-medium leading-relaxed">
                  Are you sure you want to delete this chat?
                </p>
              </div>
              <template #footer>
                <div class="flex justify-end gap-3">
                  <UButton 
                    color="gray" 
                    variant="solid" 
                    class="px-4 py-2 font-bold shadow-sm bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200 transition-colors"
                    @click="isDeleteChatModalOpen = false"
                  >
                    Cancel
                  </UButton>
                  
                  <UButton 
                    color="red" 
                    variant="solid" 
                    class="px-4 py-2 font-bold shadow-md bg-red-600 hover:bg-red-700 dark:bg-red-600 dark:hover:bg-red-700 text-white transition-colors"
                    @click="confirmDeleteChat"
                  >
                    Yes, Delete Chat
                  </UButton>
                </div>
              </template>
            </UCard>
          </div>
        </transition>

        <transition name="info-fade">
          <div v-if="isInfoModalOpen" class="fixed inset-0 z-[995] flex items-center justify-center bg-gray-950/70 backdrop-blur-sm p-4 sm:p-6" @click.self="isInfoModalOpen = false">
            <UCard class="w-full max-w-lg bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-2xl overflow-hidden" :ui="{ divide: 'divide-y divide-gray-100 dark:divide-gray-800', body: 'p-6' }">
              <template #header>
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2 text-primary-600 dark:text-primary-400">
                    <UIcon name="i-lucide-info" class="w-6 h-6" />
                    <h3 class="text-xl font-black tracking-wide uppercase text-gray-900 dark:text-white">How to use the Chatbot</h3>
                  </div>
                  <UButton color="gray" variant="ghost" icon="i-lucide-x" class="-my-1" @click="isInfoModalOpen = false" />
                </div>
              </template>
              
              <div class="space-y-6 py-2">
                <p class="text-base text-gray-600 dark:text-gray-400 leading-relaxed">
                  Welcome! The <b>DuoSigna Sign Tutor</b> is designed to be your comprehensive assistant in learning American Sign Language. You can use it in the following ways:
                </p>
                <div class="space-y-5">
                  <div class="flex gap-4 items-start">
                    <div class="p-2 bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 rounded-xl mt-1"><UIcon name="i-lucide-help-circle" class="w-6 h-6" /></div>
                    <div>
                      <h4 class="font-bold text-gray-900 dark:text-white text-lg">General ASL Questions</h4>
                      <p class="text-sm text-gray-500 dark:text-gray-400 leading-relaxed mt-1">Ask generic questions about grammar, structure, history, or culture. Try asking: <i>"What is the grammar structure of ASL?"</i></p>
                    </div>
                  </div>
                  <div class="flex gap-4 items-start">
                    <div class="p-2 bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 rounded-xl mt-1"><UIcon name="i-lucide-book-open" class="w-6 h-6" /></div>
                    <div>
                      <h4 class="font-bold text-gray-900 dark:text-white text-lg">Sign Descriptions & Media</h4>
                      <p class="text-sm text-gray-500 dark:text-gray-400 leading-relaxed mt-1">Ask how to perform a specific sign or letter. The chatbot will provide detailed textual instructions and attach a high-quality reference Video or GIF directly inside the chat message.</p>
                    </div>
                  </div>
                  <div class="flex gap-4 items-start">
                    <div class="p-2 bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 rounded-xl mt-1"><UIcon name="i-lucide-camera" class="w-6 h-6" /></div>
                    <div>
                      <h4 class="font-bold text-gray-900 dark:text-white text-lg">Real-time Sign Recognition</h4>
                      <p class="text-sm text-gray-500 dark:text-gray-400 leading-relaxed mt-1">Once the tutor gives you the explanation for a valid word, click <b>"Activate Camera"</b> to launch the dashboard. Review the instructions and try the sign: if the AI recognizes it with at least <b class="text-primary-600 dark:text-primary-400">65% accuracy</b>, it will be saved to your permanent dictionary!</p>
                    </div>
                  </div>
                </div>
              </div>

              <template #footer>
                <div class="flex justify-end">
                  <UButton color="primary" variant="solid" size="md" class="px-6 py-2.5 font-bold rounded-xl shadow-md" @click="isInfoModalOpen = false">Got it!</UButton>
                </div>
              </template>
            </UCard>
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
/* 1. Modale Invito Fotocamera (Messaggio nella chat) */
.fade-enter-active, .fade-leave-active { transition: opacity 0.4s ease, transform 0.4s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateY(10px); }

/* 2. Dashboard Camera (Tutto schermo) */
.camera-fade-enter-active, .camera-fade-leave-active { transition: opacity 0.4s ease, transform 0.4s ease; }
.camera-fade-enter-from, .camera-fade-leave-to { opacity: 0; transform: scale(0.97); }

/* 3. Modale Zoom Media (Effetto lente di ingrandimento) */
.zoom-fade-enter-active, .zoom-fade-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.zoom-fade-enter-from, .zoom-fade-leave-to { opacity: 0; transform: scale(0.9); }

/* 4. Modale Info Onboarding */
.info-fade-enter-active, .info-fade-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.info-fade-enter-from, .info-fade-leave-to { opacity: 0; transform: translateY(10px); }

/* 5. Alerts Successo e Warning */
.slide-down-enter-active, .slide-down-leave-active {
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.slide-down-enter-from, .slide-down-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

/* Scrollbar nascosta per la sidebar della fotocamera */
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; transform: scale(0.95); }

</style>
