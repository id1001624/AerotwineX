<template>
  <div id="app">
    <FlightSearch />
  </div>
</template>

<script>
import FlightSearch from './components/FlightSearch.vue'

export default {
  name: 'App',
  components: {
    FlightSearch
  }
}
</script>

<style>
body {
  margin: 0;
  padding: 0;
  background-color: #f5f5f5;
  font-family: 'Noto Sans TC', Arial, sans-serif;
}

#app {
  width: 100%;
  min-height: 100vh;
}
</style>