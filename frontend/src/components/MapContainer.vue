<template>
    <div id="map-container" :class="{ loading: isLoading }">
      <!-- 显示错误信息 -->
      <div v-if="errorMessage" class="error-message">
        错误: {{ errorMessage }}
      </div>
      <!-- 加载提示 -->
      <div v-if="isLoading && !errorMessage" class="loading-overlay">
        正在加载城市数据并初始化地图...
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref, onMounted, onUnmounted } from 'vue';
  import axios from 'axios'; // 引入 axios
  
  // --- 后端 API 配置 ---
  // 后端 Flask API 的基础 URL，确保端口号与 Flask 运行的端口一致
  // 在开发时通常是 http://localhost:5000
  // 在生产环境中，你需要将其替换为你的后端部署地址
  const BACKEND_API_BASE_URL = 'http://127.0.0.1:5000';
  
  // --- 地图样式配置 ---
  const polygonStyle = {
    fillColor: '#00B2D5',
    strokeColor: '#fff',
    strokeWeight: 1,
    fillOpacity: 0.6,
  };
  const labelStyle = {
    color: '#ffffff',
    fontSize: '12px',
    backgroundColor: 'rgba(0,0,0,0.5)',
    padding: '2px 5px',
    border: 'none',
    borderRadius: '3px',
  };
  // --- 配置结束 ---
  
  const map = ref(null);
  const districtSearch = ref(null);
  const drawnPolygons = ref([]);
  const drawnLabels = ref([]);
  const citiesToHighlight = ref([]); // 初始化为空数组
  const isLoading = ref(true); // 添加加载状态
  const errorMessage = ref(''); // 用于显示错误信息
  
  // --- 数据获取 (调用后端 API) ---
  const fetchCitiesFromBackend = async () => {
    isLoading.value = true; // 开始加载
    errorMessage.value = ''; // 清除旧错误
  
    const apiUrl = `api/get-cities`; // 构建 API URL
  
    try {
      console.log(`正在从后端 API 获取城市列表: ${apiUrl}`);
      // 使用 axios GET 请求调用我们的 Flask 后端
      const response = await axios.get(apiUrl);
  
      // 检查后端是否成功返回数据 (Flask 返回的是一个数组)
      if (Array.isArray(response.data)) {
          citiesToHighlight.value = response.data; // 更新 ref
          console.log('从后端获取到的城市列表:', citiesToHighlight.value);
          if (citiesToHighlight.value.length === 0) {
              console.warn('后端返回了空的城市列表。');
              // 可以选择性地显示一个提示信息
              // errorMessage.value = '未找到需要高亮的城市数据。';
          }
      } else {
           // 如果后端返回的不是预期的数组格式
           console.error('后端 API 返回的数据格式不正确:', response.data);
           errorMessage.value = '无法解析从服务器获取的城市数据。';
           citiesToHighlight.value = [];
      }
  
    } catch (error) {
      console.error('从后端 API 获取数据失败:', error);
      if (error.response) {
        // 后端返回了具体的错误信息 (例如 4xx, 5xx)
        const backendError = error.response.data?.error || `HTTP ${error.response.status}`;
        errorMessage.value = `加载城市数据失败: ${backendError}`;
        console.error('后端错误详情:', error.response.data);
      } else if (error.request) {
        // 请求已发出，但没有收到响应 (网络问题或后端未运行)
        errorMessage.value = '无法连接到城市数据服务，请检查后端是否运行或网络连接。';
      } else {
        // 设置请求时发生了一些事情
        errorMessage.value = `请求失败: ${error.message}`;
      }
      citiesToHighlight.value = []; // 出错时清空列表
    } finally {
      // 数据加载（无论成功或失败）完成后，再尝试初始化地图
      isLoading.value = false; // 结束加载状态
      initMap(); // 在数据获取完成后初始化地图
    }
  };
  
  
  // --- 地图相关函数 (initMap, performMapInitialization, highlightCities, clearHighlights) ---
  // 这部分函数基本保持不变，因为它们依赖于 citiesToHighlight.value 的内容，
  // 而 fetchCitiesFromBackend 负责更新这个 ref。
  
  const initMap = () => {
    if (!window.AMap) {
      console.error('高德地图 JS API 未加载完成');
      errorMessage.value = '正在等待高德地图API加载...'; // 提示用户
      const checkInterval = setInterval(() => {
        if (window.AMap) {
          clearInterval(checkInterval);
          console.log('AMap API 加载成功，开始初始化地图。');
          errorMessage.value = ''; // 清除等待信息
          performMapInitialization();
        }
      }, 500);
      setTimeout(() => {
          if (!window.AMap) {
              clearInterval(checkInterval);
              console.error('AMap API 加载超时！');
              errorMessage.value = '高德地图加载超时，请刷新页面重试。';
              isLoading.value = false; // 确保加载状态解除
          }
      }, 15000); // 增加超时时间
      return;
    }
    performMapInitialization();
  };
  
  const performMapInitialization = () => {
      if (map.value) return;
  
      try {
          map.value = new AMap.Map('map-container', {
              zoom: 5,
              center: [106.397428, 35.90923], // 中国中心点
              viewMode: '3D',
              mapStyle: 'amap://styles/darkblue', // 使用深蓝风格
          });
  
          districtSearch.value = new AMap.DistrictSearch({
              level: 'city',    // 查询级别为市
              subdistrict: 0,   // 不获取子行政区
              extensions: 'all', // 获取边界和中心点
          });
  
          map.value.on('complete', () => {
              console.log('地图加载完成');
              // 只有在城市列表不为空时才进行高亮
              if (citiesToHighlight.value.length > 0) {
                  highlightCities();
              } else if (!errorMessage.value) { // 避免覆盖错误信息
                  console.log('没有需要高亮的城市数据。');
                  // 可以选择在这里也给用户一个提示
                  // errorMessage.value = '没有需要高亮的城市数据。';
              }
          });
  
          map.value.on('error', (e) => {
              console.error('地图加载或操作错误:', e);
              errorMessage.value = '地图发生错误，请稍后重试。';
          });
  
      } catch (mapError) {
          console.error("初始化地图时捕获到错误:", mapError);
          errorMessage.value = '初始化地图失败，请检查浏览器兼容性或网络。';
          isLoading.value = false; // 确保加载状态解除
      }
  };
  
  const highlightCities = () => {
    if (!districtSearch.value || !map.value || citiesToHighlight.value.length === 0) {
        console.log('高亮条件不满足（地图未准备好或无城市数据）');
        return;
    }
  
    clearHighlights(); // 先清除旧的
  
    console.log(`开始高亮 ${citiesToHighlight.value.length} 个城市...`);
  
    const promises = citiesToHighlight.value.map(cityName => {
      return new Promise((resolve, reject) => {
          districtSearch.value.search(cityName, (status, result) => {
              // console.log(`查询 '${cityName}' 结果:`, status, result); // 调试日志
              if (status === 'complete' && result.info === 'OK' && result.districtList && result.districtList.length > 0) {
                  const districtInfo = result.districtList[0];
                  const bounds = districtInfo.boundaries;
                  const center = districtInfo.center; // 获取中心点
  
                  if (bounds && bounds.length > 0) {
                      bounds.forEach(bound => {
                          if (bound && bound.length > 0) { // 检查边界数据有效性
                              const polygon = new AMap.Polygon({
                                  path: bound,
                                  ...polygonStyle, // 应用统一样式
                                  map: map.value,
                                  // 可选：添加自定义属性以便识别
                                  // extData: { type: 'cityHighlight', name: cityName }
                              });
                              drawnPolygons.value.push(polygon);
                          } else {
                             console.warn(`城市 '${cityName}' 的边界数据无效。`);
                          }
                      });
                  } else {
                       console.warn(`城市 '${cityName}' 未找到有效的边界数据。`);
                  }
  
                  if (center) {
                      const textLabel = new AMap.Text({
                          text: cityName,
                          position: center,
                          style: labelStyle, // 应用统一样式
                          map: map.value,
                          // 可选：添加自定义属性
                          // extData: { type: 'cityLabel', name: cityName }
                      });
                      drawnLabels.value.push(textLabel);
                  } else {
                       console.warn(`城市 '${cityName}' 未找到有效的中心点坐标。`);
                  }
                  resolve(cityName); // 当前城市处理完成
  
              } else if (status === 'no_data') {
                   console.warn(`高德地图查询行政区 '${cityName}' 无数据:`, result);
                   resolve(cityName); // 查不到也算完成，避免阻塞其他城市
              } else {
                  console.error(`高德地图查询行政区 '${cityName}' 失败:`, status, result);
                  reject(new Error(`查询 ${cityName} 失败: ${status}, ${result.info}`)); // 查询失败
              }
          });
      });
    });
  
    // 等待所有查询和绘制操作（或失败）
    Promise.allSettled(promises).then(results => {
        console.log('所有城市高亮处理完成。');
        const successfulCities = results.filter(r => r.status === 'fulfilled').map(r => r.value);
        const failedCities = results.filter(r => r.status === 'rejected').map(r => r.reason.message); // 获取失败原因中的城市名
  
        console.log('成功处理的城市:', successfulCities);
        if (failedCities.length > 0) {
            console.warn(`查询或绘制失败的城市 (${failedCities.length}个):`, failedCities);
            // 可以选择性地给用户一个提示
            // errorMessage.value = `部分城市 (${failedCities.join(', ')}) 加载失败。`;
        }
  
        // 可选：在所有绘制完成后调整视野以适应所有高亮区域
        if (drawnPolygons.value.length > 0) {
          //   map.value.setFitView(drawnPolygons.value, false, [60, 60, 60, 60], 12); // 调整视野
        }
    });
  };
  
  const clearHighlights = () => {
      if (map.value) {
          // 使用 AMap 实例的 remove 方法一次性移除所有覆盖物
          map.value.remove(drawnPolygons.value);
          map.value.remove(drawnLabels.value);
      }
      drawnPolygons.value = []; // 清空数组引用
      drawnLabels.value = [];   // 清空数组引用
      // console.log('已清除所有高亮和标签');
  };
  
  
  // --- 生命周期钩子 ---
  onMounted(async () => {
    // 先从后端获取城市数据
    await fetchCitiesFromBackend();
    // 数据获取完成后 (无论成功与否)，会调用 initMap() 来初始化地图
    // initMap 内部会处理 AMap API 的加载检查
  });
  
  onUnmounted(() => {
    clearHighlights(); // 组件卸载前清除地图上的覆盖物
    if (map.value) {
      map.value.destroy();
      map.value = null;
      console.log('地图实例已销毁');
    }
  });
  
  </script>
  
  <style scoped>
  #map-container {
    position: relative; /* 为了定位覆盖层 */
    width: 100vw;
    height: 100vh;
    background-color: #0f1c30; /* 深蓝色背景，防止地图加载时闪烁白色 */
  }
  
  .loading-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.7);
    color: white;
    display: flex;
    justify-content: center;
    align-items: center;
    font-size: 1.2em;
    z-index: 10; /* 确保在地图之上 */
    text-align: center;
    padding: 20px;
  }
  
  .error-message {
    position: absolute;
    top: 10px;
    left: 50%;
    transform: translateX(-50%);
    background-color: rgba(220, 53, 69, 0.9); /* 更明显的红色 */
    color: white;
    padding: 10px 15px;
    border-radius: 5px;
    z-index: 11; /* 比加载提示更高 */
    max-width: 80%;
    text-align: center;
    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
  }
  </style>
  