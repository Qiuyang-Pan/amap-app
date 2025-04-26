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
  const BACKEND_API_BASE_URL = 'http://127.0.0.1:5001';

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

  // --- 缓存配置 ---
  const CACHE_PREFIX = 'cityGeoData_'; // localStorage 缓存键前缀
  // --- 配置结束 ---

  const map = ref(null);
  const districtSearch = ref(null);
  const drawnPolygons = ref([]);
  const drawnLabels = ref([]);
  const citiesToHighlight = ref([]);
  const isLoading = ref(true);
  const errorMessage = ref('');

  // --- 数据获取 (调用后端 API) ---
  const fetchCitiesFromBackend = async () => {
    isLoading.value = true; // 开始加载
    errorMessage.value = ''; // 清除旧错误
  
    const apiUrl = `api/get-cities`; // 构建 API URL
  
    try {
      console.log(`正在从后端 API 获取城市列表: ${apiUrl}`);
      const response = await axios.get(apiUrl);

      if (Array.isArray(response.data)) {
          citiesToHighlight.value = response.data;
          console.log('从后端获取到的城市列表:', citiesToHighlight.value);
          if (citiesToHighlight.value.length === 0) {
              console.warn('后端返回了空的城市列表。');
          }
      } else {
           console.error('后端 API 返回的数据格式不正确:', response.data);
           errorMessage.value = '无法解析从服务器获取的城市数据。';
           citiesToHighlight.value = [];
      }

    } catch (error) {
      console.error('从后端 API 获取数据失败:', error);
      if (error.response) {
        const backendError = error.response.data?.error || `HTTP ${error.response.status}`;
        errorMessage.value = `加载城市数据失败: ${backendError}`;
        console.error('后端错误详情:', error.response.data);
      } else if (error.request) {
        errorMessage.value = '无法连接到城市数据服务，请检查后端是否运行或网络连接。';
      } else {
        errorMessage.value = `请求失败: ${error.message}`;
      }
      citiesToHighlight.value = [];
    } finally {
      isLoading.value = false;
      // 确保在地图初始化完成后再尝试高亮
      // initMap() 会处理地图加载，并在完成后调用 highlightCities (如果需要)
      initMap();
    }
  };

  // --- 地图相关函数 (initMap, performMapInitialization, highlightCities, clearHighlights) ---

  const initMap = () => {
    if (!window.AMap) {
      console.error('高德地图 JS API 未加载完成');
      errorMessage.value = '正在等待高德地图API加载...';
      const checkInterval = setInterval(() => {
        if (window.AMap) {
          clearInterval(checkInterval);
          console.log('AMap API 加载成功，开始初始化地图。');
          errorMessage.value = '';
          performMapInitialization();
        }
      }, 500);
      setTimeout(() => {
          if (!window.AMap) {
              clearInterval(checkInterval);
              console.error('AMap API 加载超时！');
              errorMessage.value = '高德地图加载超时，请刷新页面重试。';
              isLoading.value = false;
          }
      }, 15000);
      return;
    }
    performMapInitialization();
  };

  const performMapInitialization = () => {
      if (map.value) return;

      try {
          map.value = new AMap.Map('map-container', {
              zoom: 5,
              center: [106.397428, 35.90923],
              viewMode: '3D',
              mapStyle: 'amap://styles/darkblue',
          });

          districtSearch.value = new AMap.DistrictSearch({
              level: 'city',
              subdistrict: 0,
              extensions: 'all',
          });

          map.value.on('complete', () => {
              console.log('地图加载完成');
              // 只有在地图和 districtSearch 准备好，并且有城市数据时才高亮
              if (citiesToHighlight.value.length > 0 && districtSearch.value) {
                  highlightCities();
              } else if (!errorMessage.value) {
                  console.log('没有需要高亮的城市数据或地图服务未就绪。');
              }
          });

          map.value.on('error', (e) => {
              console.error('地图加载或操作错误:', e);
              errorMessage.value = '地图发生错误，请稍后重试。';
          });

      } catch (mapError) {
          console.error("初始化地图时捕获到错误:", mapError);
          errorMessage.value = '初始化地图失败，请检查浏览器兼容性或网络。';
          isLoading.value = false;
      }
  };

  // --- 绘制函数 (独立出来，方便复用) ---
  const drawCityFeature = (cityName, boundaries, center) => {
      let polygonsAddedInCity = 0;
      if (boundaries && boundaries.length > 0) {
          boundaries.forEach((bound, index) => {
              if (bound && bound.length > 0) {
                  try {
                      const polygon = new AMap.Polygon({
                          path: bound,
                          ...polygonStyle,
                          map: map.value,
                      });
                      drawnPolygons.value.push(polygon);
                      polygonsAddedInCity++;
                  } catch(e) {
                      console.error(`[${cityName}] 绘制多边形 #${index + 1} 出错:`, e);
                  }
              } else {
                  console.warn(`[${cityName}] 边界数据 #${index + 1} 无效.`);
              }
          });
      } else {
          console.warn(`[${cityName}] 未找到有效的边界数据.`);
      }

      if (center && polygonsAddedInCity > 0) { // 只有成功绘制了至少一个多边形才添加标签
          try {
              // 注意：从 localStorage 恢复的 center 可能是普通对象 {lng, lat}
              // AMap.Text 构造函数可以接受这种格式
              const textLabel = new AMap.Text({
                  text: cityName,
                  position: center, // 可以是 AMap.LngLat 或 {lng, lat}
                  style: labelStyle,
                  map: map.value,
              });
              drawnLabels.value.push(textLabel);
          } catch(e) {
              console.error(`[${cityName}] 绘制文本标签出错:`, e);
          }
      } else if (!center) {
          console.warn(`[${cityName}] 未找到有效的中心点.`);
      } else {
          // console.log(`[${cityName}] 没有绘制多边形，跳过标签.`);
      }
      return polygonsAddedInCity > 0; // 返回是否成功绘制了任何内容
  }

  // --- !! 修改后的 highlightCities 函数 !! ---
  const highlightCities = async (batchSize = 3, delayBetweenBatches = 1000) => { // 调整批次大小和延时
      // 1. 前置条件检查
      if (!districtSearch.value || !map.value || !citiesToHighlight.value || citiesToHighlight.value.length === 0) {
          console.warn('[HighlightCities] 中止: 初始条件不满足 (地图/搜索未就绪或无城市数据).');
          return;
      }
      // 2. 清理并准备
      clearHighlights();
      const cities = [...citiesToHighlight.value];
      console.log(`[HighlightCities] 开始分批处理 ${cities.length} 个城市。批大小: ${batchSize}, 批间延时: ${delayBetweenBatches}ms`);
      const allResults = [];
      let cacheHits = 0; // 记录缓存命中次数

      // 3. 分批处理循环
      for (let i = 0; i < cities.length; i += batchSize) {
          const batch = cities.slice(i, i + batchSize);
          console.log(`[HighlightCities] 处理批次 #${Math.floor(i / batchSize) + 1} (${batch.length} 个城市):`, batch);

          // 4. 创建当前批次的查询/绘制 Promises
          const batchPromises = batch.map(cityName => {
              return new Promise(async (resolve) => { // 使用 async 以便在内部 await
                  const cacheKey = `${CACHE_PREFIX}${cityName}`;
                  let processed = false; // 标记是否已处理（从缓存或 API）

                  // ---- 尝试从 localStorage 读取缓存 ----
                  try {
                      const cachedDataString = localStorage.getItem(cacheKey);
                      if (cachedDataString) {
                          let cachedData = null;
                          try {
                              cachedData = JSON.parse(cachedDataString);
                          } catch (parseError) {
                              console.warn(`[${cityName}] 解析缓存数据失败，将重新请求:`, parseError);
                              localStorage.removeItem(cacheKey); // 删除损坏的缓存
                          }

                          // 检查缓存数据是否有效
                          if (cachedData && cachedData.boundaries && cachedData.center) {
                              console.log(`[${cityName}] 缓存命中，使用缓存数据绘制。`);
                              const drawn = drawCityFeature(cityName, cachedData.boundaries, cachedData.center);
                              cacheHits++;
                              processed = true;
                              resolve({ status: 'fulfilled', value: cityName, source: 'cache', drawn: drawn });
                          }
                      }
                  } catch (storageReadError) {
                      console.error(`[${cityName}] 读取 localStorage 时出错:`, storageReadError);
                      // 出错则继续尝试 API 请求
                  }
                  // ---- 缓存读取结束 ----

                  // 如果已从缓存处理，则跳过 API 请求
                  if (processed) return;

                  // ---- 缓存未命中 或 读取失败，执行 API 请求 ----
                  console.log(`[${cityName}] 缓存未命中或无效，发起 districtSearch.search()...`);
                  districtSearch.value.search(cityName, (status, result) => {
                    // console.log(`[${cityName}] Search callback received. Status: ${status}, Info: ${result?.info}`);
                    try {
                        if (status === 'complete' && result.info === 'OK' && result.districtList && result.districtList.length > 0) {
                            const districtInfo = result.districtList[0];
                            const boundaries = districtInfo.boundaries;
                            const center = districtInfo.center; // 获取中心点

                            // 绘制
                            const drawn = drawCityFeature(cityName, boundaries, center);

                            // ---- 缓存 API 结果 ----
                            if (boundaries && center) { // 只有在获取到有效数据时才缓存
                                const dataToCache = { boundaries: boundaries, center: center };
                                try {
                                    localStorage.setItem(cacheKey, JSON.stringify(dataToCache));
                                    console.log(`[${cityName}] API 数据已缓存.`);
                                } catch (storageWriteError) {
                                    console.error(`[${cityName}] 写入 localStorage 失败:`, storageWriteError);
                                    // 即使缓存失败，绘制仍然完成
                                }
                            }
                            // ---- 缓存结束 ----

                            console.log(`[${cityName}] API 请求成功并处理完毕.`);
                            resolve({ status: 'fulfilled', value: cityName, source: 'api', drawn: drawn });

                        } else if (status === 'no_data') {
                            console.warn(`[${cityName}] API 返回 'no_data'. Result:`, result);
                            resolve({ status: 'fulfilled', value: cityName, source: 'api', drawn: false }); // 无数据也视为处理完成（但无绘制）
                        } else {
                            console.error(`[${cityName}] API 搜索失败! Status: ${status}, Info: ${result?.info}`);
                            resolve({ status: 'rejected', reason: new Error(`查询 ${cityName} 失败: Status=${status}, Info=${result?.info}`) });
                        }
                    } catch (processError) {
                       console.error(`[${cityName}] 处理 API 结果或绘制时出错:`, processError);
                       resolve({ status: 'rejected', reason: new Error(`处理或绘制 ${cityName} 时出错: ${processError.message}`) });
                    }
                  });
                  // ---- API 请求结束 ----
              });
          });

          // 5. 等待当前批次的所有 Promise 完成 (无论成功、失败、缓存命中)
          const batchResults = await Promise.allSettled(batchPromises); // 使用 allSettled 获取所有结果
          allResults.push(...batchResults);

          // 6. 批间延时
          if (i + batchSize < cities.length && delayBetweenBatches > 0) {
              console.log(`[HighlightCities] 等待 ${delayBetweenBatches}ms 后进行下一批...`);
              await new Promise(resolve => setTimeout(resolve, delayBetweenBatches));
          }
      }

      // 7. 所有批次处理完毕，分析最终结果
      console.log('[HighlightCities] 所有批次处理完毕。');
      const successfulOperations = allResults.filter(r => r.status === 'fulfilled');
      const failedOperations = allResults.filter(r => r.status === 'rejected');

      const drawnCount = successfulOperations.filter(r => r.value.drawn).length; // 统计实际绘制了内容的城市数量

      console.log(`[HighlightCities] 总结: ${successfulOperations.length} 个操作成功完成 (${cacheHits} 次来自缓存), ${failedOperations.length} 个操作失败。总共为 ${drawnCount} 个城市绘制了图形。`);

      if (failedOperations.length > 0) {
          const failedMessages = failedOperations.map(r => r.reason.message);
          console.warn(`[HighlightCities] 失败的操作详情 (${failedOperations.length}):`, failedMessages);
          // 可以选择性更新 errorMessage，但注意不要覆盖后端加载错误
          // errorMessage.value = `部分城市 (${failedMessages.join(', ')}) 加载失败。`;
      }

      // 8. 可选：调整视野
      if (drawnPolygons.value.length > 0) {
          console.log('[HighlightCities] 可选: 暂时跳过 map.setFitView()。');
          // try {
          //   map.value.setFitView(drawnPolygons.value, false, [60, 60, 60, 60], 12);
          // } catch (fitViewError) {
          //   console.error('[HighlightCities] 调用 setFitView 出错:', fitViewError);
          // }
      }
      console.log('[HighlightCities] highlightCities 函数执行完毕。');
  };
  // --- highlightCities 修改结束 ---


  const clearHighlights = () => {
      if (map.value) {
          // 优化：一次性移除所有覆盖物比循环移除性能更好
          const overlaysToRemove = [...drawnPolygons.value, ...drawnLabels.value];
          if (overlaysToRemove.length > 0) {
              map.value.remove(overlaysToRemove);
          }
      }
      drawnPolygons.value = [];
      drawnLabels.value = [];
      // console.log('已清除所有高亮和标签');
  };


  // --- 生命周期钩子 ---
  onMounted(async () => {
    // 先从后端获取城市数据
    await fetchCitiesFromBackend();
    // fetchCitiesFromBackend 的 finally 块中会调用 initMap()
    // initMap 会负责检查 AMap API 加载情况并初始化地图
    // 地图初始化完成的回调 ('complete') 中会检查是否有城市数据并调用 highlightCities
  });

  onUnmounted(() => {
    clearHighlights();
    if (map.value) {
      map.value.destroy();
      map.value = null;
      console.log('地图实例已销毁');
    }
    // 清理 districtSearch 实例 (虽然通常地图销毁会处理，但显式清理更好)
    districtSearch.value = null;
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
