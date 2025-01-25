<template>
  <div id="app">
    <h1>Chatbot</h1>
    <Chatbot />
  </div>
</template>

<script>
import Chatbot from './components/Chatbot.vue';

export default {
  name: 'App',
  components: {
    Chatbot
  }
};
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}
</style>
