<template>
  <MapContainer />
</template>

<script setup>
import MapContainer from './components/MapContainer.vue';
</script>

<style>
/* 添加一些全局样式，移除默认的边距和内边距 */
body, html {
  margin: 0;
  padding: 0;
  height: 100%;
  width: 100%;
  overflow: hidden; /* 防止滚动条出现 */
}

#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  width: 100%;
  height: 100%;
}
</style>
