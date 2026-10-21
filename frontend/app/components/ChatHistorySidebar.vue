<script setup>
import { ref } from 'vue'

const props = defineProps({
  chats: {
    type: Array,
    default: () => []
  },
  currentChatId: {
    type: [String, Number, null],
    default: null
  }
})

const emit = defineEmits(['select-chat', 'new-chat', 'delete-chat'])

const isSidebarOpen = ref(true)

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value
}
</script>

<template>
  <div 
    class="flex flex-col border-l border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 transition-all duration-300 sticky top-16 h-[calc(100vh-4rem)] overflow-y-auto overflow-x-hidden shadow-sm"
    :class="isSidebarOpen ? 'w-72 px-4 py-6' : 'w-20 px-2 py-6 items-center'"
  >
    <div class="flex items-center mb-6 gap-3" :class="!isSidebarOpen ? 'flex-col gap-4' : ''">
      <UButton 
        :icon="isSidebarOpen ? 'i-lucide-panel-right-close' : 'i-lucide-panel-right-open'" 
        color="gray" 
        variant="ghost" 
        class="hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors"
        @click="toggleSidebar" 
        aria-label="Toggle History Sidebar"
      />
      <span v-if="isSidebarOpen" class="font-bold text-lg text-gray-900 dark:text-white tracking-tight">
        Chat History
      </span>
    </div>

    <div class="mb-6 w-full" :class="!isSidebarOpen ? 'flex justify-center' : ''">
      <UButton 
        icon="i-lucide-plus" 
        :label="isSidebarOpen ? 'New Chat' : ''" 
        :color="currentChatId ? 'primary' : 'gray'" 
        variant="soft" 
        size="md"
        class="w-full font-bold transition-all duration-200 shadow-sm"
        :class="[
          isSidebarOpen ? 'justify-start px-4' : 'justify-center',
          !currentChatId ? 'opacity-60 cursor-not-allowed' : 'hover:scale-105'
        ]"
        @click="emit('new-chat')"
      />
    </div>

    <div class="flex-1 overflow-y-auto space-y-2 w-full custom-scrollbar pr-1" v-if="chats.length > 0">
      <div 
        v-for="chat in chats" 
        :key="chat.id"
        class="group flex items-center justify-between rounded-xl cursor-pointer transition-all duration-200"
        :class="[
          chat.id === currentChatId 
            ? 'bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300' 
            : 'hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300',
          isSidebarOpen ? 'p-3' : 'p-3 justify-center'
        ]"
        @click="emit('select-chat', chat.id)"
      >
        <div class="flex items-center gap-3 overflow-hidden">
          <UIcon name="i-lucide-message-square" class="w-5 h-5 flex-shrink-0 opacity-70" />
          <span v-if="isSidebarOpen" class="text-sm font-medium truncate w-36">
            {{ chat.title }}
          </span>
        </div>
        
        <div v-if="isSidebarOpen" class="opacity-0 group-hover:opacity-100 transition-opacity flex items-center">
          <UButton 
            icon="i-lucide-trash-2" 
            color="red" 
            variant="ghost" 
            size="xs" 
            class="hover:bg-red-100 dark:hover:bg-red-900/50"
            @click.stop="emit('delete-chat', chat.id)"
          />
        </div>
      </div>
    </div>

    <div v-else class="flex flex-col items-center justify-center h-full opacity-50 text-center mt-10">
      <UIcon name="i-lucide-history" class="w-10 h-10 mb-2" />
      <span v-if="isSidebarOpen" class="text-sm font-medium">No chat history</span>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: rgba(156, 163, 175, 0.5); /* gray-400 */
  border-radius: 20px;
}
</style>