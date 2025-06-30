<template>
  <div class="dashboard">

    <a-row :gutter="12" class="stat-cards">
      <a-col :span="6">
        <a-card :loading="loading" :bordered="false">
          <template #title>
            <span>
              <ProjectOutlined /> 项目总数
            </span>
          </template>
          <div class="card-content">
            <h2>{{ stats.project_count || 0 }}</h2>
            <p class="card-subtitle">总构建: <span class="build-text">{{ stats.total_builds_count || 0 }}</span> | 任务: <span class="task-text">{{ stats.task_count || 0 }}</span></p>
          </div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card :loading="loading" :bordered="false">
          <template #title>
            <span>
              <UserOutlined /> 用户总数
            </span>
          </template>
          <div class="card-content">
            <h2>{{ stats.user_count || 0 }}</h2>
            <p class="card-subtitle">环境数量: {{ stats.env_count || 0 }}</p>
          </div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card :loading="loading" :bordered="false">
          <template #title>
            <span>
              <BuildOutlined /> 构建成功率
            </span>
          </template>
          <div class="card-content">
            <h2>{{ stats.success_rate || 0 }}%</h2>
            <p class="card-subtitle">最近7天: {{ stats.total_recent_builds || 0 }} 次构建</p>
          </div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card :loading="loading" :bordered="false">
          <template #title>
            <span>
              <ClockCircleOutlined /> 今日构建
            </span>
          </template>
          <div class="card-content">
            <h2>{{ todayBuilds.length }}</h2>
            <p class="card-subtitle">成功: <span class="success-text">{{ successBuilds }}</span> | 失败: <span class="failed-text">{{ failedBuilds }}</span></p>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="12" class="chart-row">
      <a-col :span="16">
        <a-card title="构建任务趋势" :loading="trendLoading" :bordered="false">
          <div class="chart-container" ref="trendChartRef"></div>
        </a-card>
      </a-col>

      <a-col :span="8">
        <a-card title="项目类型分布" :loading="distributionLoading" :bordered="false">
          <div class="chart-container" ref="pieChartRef"></div>
        </a-card>
      </a-col>
    </a-row>

    <a-card title="最近构建任务" class="recent-builds" :loading="recentLoading" :bordered="false">
      <a-table
        :columns="buildColumns"
        :data-source="recentBuilds"
        :pagination="{ pageSize: 5, size: 'small' }"
        size="small"
        :scroll="{ x: 1000 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <span :class="['status-text', `status-${record.status}`]">
              {{ getStatusText(record.status) }}
            </span>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, onBeforeUnmount, nextTick } from 'vue';
import {
  ProjectOutlined,
  UserOutlined,
  BuildOutlined,
  ClockCircleOutlined
} from '@ant-design/icons-vue';
import axios from 'axios';
import * as echarts from 'echarts/core';
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  ToolboxComponent,
} from 'echarts/components';
import { LineChart, PieChart } from 'echarts/charts';
import { UniversalTransition } from 'echarts/features';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  ToolboxComponent,
  LineChart,
  PieChart,
  CanvasRenderer,
  UniversalTransition
]);

// 状态变量
const loading = ref(false);
const trendLoading = ref(false);
const distributionLoading = ref(false);
const recentLoading = ref(false);

// 数据变量
const stats = ref({});
const trendData = ref({ dates: [], success: [], failed: [] });
const distributionData = ref([]);
const recentBuilds = ref([]);
const todayBuilds = ref([]);

// 图表引用
const trendChartRef = ref(null);
const pieChartRef = ref(null);

// 图表实例
let trendChart = null;
let pieChart = null;

// 计算属性
const successBuilds = computed(() => {
  return todayBuilds.value.filter(build => build.status === 'success').length;
});

const failedBuilds = computed(() => {
  return todayBuilds.value.filter(build => build.status === 'failed').length;
});

// 表格列定义
const buildColumns = [
  {
    title: '任务名称',
    dataIndex: 'task_name',
    key: 'task_name',
    ellipsis: true,
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    align: 'center',
  },
  {
    title: '分支',
    dataIndex: 'branch',
    key: 'branch',
    ellipsis: true,
  },
  {
    title: '版本',
    dataIndex: 'version',
    key: 'version',
    ellipsis: true,
  },
  {
    title: '环境',
    dataIndex: 'environment',
    key: 'environment',
    width: 80,
    ellipsis: true,
  },
  {
    title: '需求',
    dataIndex: 'requirement',
    key: 'requirement',
    ellipsis: true,
  },
  {
    title: '构建时间',
    dataIndex: 'start_time',
    key: 'start_time',
  },
  {
    title: '耗时',
    dataIndex: 'duration',
    key: 'duration',
    align: 'center',
  },
  {
    title: '构建人',
    dataIndex: 'operator',
    key: 'operator',
    ellipsis: true,
  },
];

// 获取状态文本
const getStatusText = (status) => {
  const statusMap = {
    'success': '成功',
    'failed': '失败',
    'running': '运行中',
    'pending': '等待中',
    'terminated': '已终止'
  };
  return statusMap[status] || '未知';
};

// 获取首页统计数据
const fetchStats = async () => {
  loading.value = true;
  try {
    const response = await axios.get('/api/dashboard/stats/');
    if (response.data.code === 200) {
      stats.value = response.data.data;
    }
  } catch (error) {
    console.error('获取统计数据失败:', error);
  } finally {
    loading.value = false;
  }
};

// 获取构建趋势数据
const fetchTrendData = async () => {
  trendLoading.value = true;
  try {
    // 接口默认获取最近7天数据
    const response = await axios.get('/api/dashboard/build-trend/');
    if (response.data.code === 200) {
      trendData.value = response.data.data;
      // 确保数据结构完整
      if (!trendData.value.dates) trendData.value.dates = [];
      if (!trendData.value.success) trendData.value.success = [];
      if (!trendData.value.failed) trendData.value.failed = [];
    }
  } catch (error) {
    console.error('获取构建趋势数据失败:', error);
  } finally {
    trendLoading.value = false;
  }
};

// 获取项目分布数据
const fetchDistributionData = async () => {
  distributionLoading.value = true;
  try {
    const response = await axios.get('/api/dashboard/project-distribution/');
    if (response.data.code === 200) {
      distributionData.value = response.data.data || [];
    }
  } catch (error) {
    console.error('获取项目分布数据失败:', error);
  } finally {
    distributionLoading.value = false;
  }
};

// 获取最近构建任务
const fetchRecentBuilds = async () => {
  recentLoading.value = true;
  try {
    const response = await axios.get('/api/dashboard/recent-builds/');
    if (response.data.code === 200) {
      recentBuilds.value = response.data.data;
    }
  } catch (error) {
    console.error('获取最近构建任务失败:', error);
  } finally {
    recentLoading.value = false;
  }
};

// 获取今日构建数据
const fetchTodayBuilds = async () => {
  const today = new Date().toISOString().split('T')[0];
  try {
    const response = await axios.get(`/api/dashboard/build-detail/?date=${today}`);
    if (response.data.code === 200) {
      todayBuilds.value = response.data.data;
    }
  } catch (error) {
    console.error('获取今日构建数据失败:', error);
  }
};

// 使用 ECharts 渲染构建趋势图表
const renderTrendChart = () => {
  if (!trendChartRef.value) {
    console.error('Trend chart DOM element not found');
    return;
  }

  // 初始化或获取 ECharts 实例
  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value);
  } else {
    trendChart.clear(); // 清除旧配置
  }

  const { dates, success, failed } = trendData.value;

  // 更柔和的颜色配置
  const successColor = 'rgba(115, 209, 61, 0.8)';
  const failedColor = 'rgba(247, 103, 107, 0.8)';

  // ECharts 配置项
  const option = {
    animation: true,
    animationDuration: 1000,
    animationEasing: 'cubicInOut',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.96)',
      borderColor: '#e8e8e8',
      borderWidth: 1,
      padding: [12, 16],
      textStyle: {
        fontSize: 12,
        color: 'rgba(0, 0, 0, 0.75)'
      },
      shadowColor: 'rgba(0, 0, 0, 0.08)',
      shadowBlur: 16,
      shadowOffsetX: 0,
      shadowOffsetY: 4,
      formatter: function(params) {
        let result = `<div style="font-weight: 500; margin-bottom: 8px; color: rgba(0,0,0,0.85);">${params[0].axisValue}</div>`;
        params.forEach(item => {
          const color = item.seriesName === '成功构建' ? successColor : failedColor;
          const style = `display:inline-block; width:8px; height:8px; margin-right:8px; border-radius:50%; background-color:${color};`;
          result += `<div style="margin: 4px 0; display: flex; align-items: center;">
            <span style="${style}"></span>
            <span style="font-size:12px; color:rgba(0,0,0,0.65); margin-right: 8px;">${item.seriesName}：</span>
            <span style="font-weight:500; color:${color}; font-size: 13px;">${item.value}</span>
          </div>`;
        });
        return result;
      },
      axisPointer: {
        type: 'line',
        lineStyle: {
          color: 'rgba(0, 0, 0, 0.15)',
          type: 'dashed',
          width: 1
        }
      }
    },
    legend: {
      data: ['成功构建', '失败构建'],
      top: '2%',
      left: 'center',
      itemWidth: 12,
      itemHeight: 12,
      textStyle: {
        fontSize: 12,
        color: 'rgba(0, 0, 0, 0.75)'
      },
      icon: 'roundRect',
      itemGap: 24
    },
    grid: {
      left: '4%',
      right: '4%',
      bottom: '12%',
      top: '16%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLabel: {
        fontSize: 12,
        color: 'rgba(0, 0, 0, 0.65)',
        margin: 15,
        fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
        rotate: 0,
        interval: 0,
      },
      axisLine: {
        lineStyle: {
          color: '#f0f0f0'
        }
      },
      axisTick: {
        show: false
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        fontSize: 12,
        color: 'rgba(0, 0, 0, 0.65)',
        margin: 12,
        fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
        show: false  // 隐藏y轴标签
      },
      splitLine: {
        lineStyle: {
          color: '#f8f8f8',
          type: 'dashed',
          width: 1
        }
      },
      axisLine: {
        show: false
      },
      axisTick: {
        show: false
      }
    },
    series: [
      {
        name: '成功构建',
        type: 'line',
        smooth: true,
        smoothMonotone: 'x',
        data: success,
        symbol: 'circle',
        symbolSize: 4,
        showSymbol: false,
        emphasis: {
          focus: 'series',
          scale: false,
          itemStyle: {
            color: successColor,
            borderColor: '#fff',
            borderWidth: 2,
            shadowColor: 'rgba(115, 209, 61, 0.25)',
            shadowBlur: 8
          },
          lineStyle: {
            width: 2.5
          }
        },
        // 鼠标悬停时显示符号
        showAllSymbol: 'auto',
        lineStyle: {
          width: 2,
          shadowColor: 'rgba(115, 209, 61, 0.15)',
          shadowBlur: 6,
          shadowOffsetY: 2,
          cap: 'round'
        },
        itemStyle: {
          color: successColor,
          borderWidth: 2,
          borderColor: '#fff'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [{
              offset: 0, color: 'rgba(115, 209, 61, 0.15)'
            }, {
              offset: 1, color: 'rgba(115, 209, 61, 0.01)'
            }]
          },
          opacity: 0.8
        }
      },
      {
        name: '失败构建',
        type: 'line',
        smooth: true,
        smoothMonotone: 'x',
        data: failed,
        symbol: 'circle',
        symbolSize: 4,
        showSymbol: false,
        emphasis: {
          focus: 'series',
          scale: false,
          itemStyle: {
            color: failedColor,
            borderColor: '#fff',
            borderWidth: 2,
            shadowColor: 'rgba(247, 103, 107, 0.25)',
            shadowBlur: 8
          },
          lineStyle: {
            width: 2.5
          }
        },
        showAllSymbol: 'auto',
        lineStyle: {
          width: 2,
          shadowColor: 'rgba(247, 103, 107, 0.15)',
          shadowBlur: 6,
          shadowOffsetY: 2,
          cap: 'round'
        },
        itemStyle: {
          color: failedColor,
          borderWidth: 2,
          borderColor: '#fff'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [{
              offset: 0, color: 'rgba(247, 103, 107, 0.15)'
            }, {
              offset: 1, color: 'rgba(247, 103, 107, 0.01)'
            }]
          },
          opacity: 0.8
        }
      }
    ]
  };

  // 应用配置项
  trendChart.setOption(option);

  // 图表交互事件
  trendChart.on('mouseover', { seriesIndex: 0 }, function() {
    trendChart.setOption({
      series: [{
        showSymbol: true,
        symbolSize: 5
      }, {
        lineStyle: {
          opacity: 0.4
        },
        areaStyle: {
          opacity: 0.2
        }
      }]
    });
  });

  trendChart.on('mouseover', { seriesIndex: 1 }, function() {
    trendChart.setOption({
      series: [{
        lineStyle: {
          opacity: 0.4
        },
        areaStyle: {
          opacity: 0.2
        }
      }, {
        showSymbol: true,
        symbolSize: 5
      }]
    });
  });

  trendChart.on('mouseout', function() {
    trendChart.setOption({
      series: [{
        showSymbol: false,
        lineStyle: {
          opacity: 1
        },
        areaStyle: {
          opacity: 0.8
        }
      }, {
        showSymbol: false,
        lineStyle: {
          opacity: 1
        },
        areaStyle: {
          opacity: 0.8
        }
      }]
    });
  });

  // 窗口大小调整监听
  window.addEventListener('resize', handleResize);
};

//  ECharts 渲染项目分布图表
const renderPieChart = () => {
  if (!pieChartRef.value) {
    console.error('Pie chart DOM element not found');
    return;
  }

  if (!distributionData.value || distributionData.value.length === 0) {
     if (pieChart) {
       pieChart.clear(); // 清除旧图表
     }
    return;
  }

  // 获取 ECharts 实例
  if (!pieChart) {
    pieChart = echarts.init(pieChartRef.value);
  } else {
    pieChart.clear(); // 清除旧配置
  }


  const pieData = distributionData.value.map((item, index) => {
    const colors = [
      'rgba(22,119,255,0.6)', 
      'rgba(82, 196, 26, 0.6)',
    ];

    return {
      name: item.type,
      value: item.value,
      itemStyle: {
        color: colors[index % colors.length]
      }
    };
  });

  // ECharts 配置项
  const option = {
    animation: true,
    animationDuration: 600,
    animationEasing: 'cubicOut',
    animationDelay: 0,
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b} : {c} ({d}%)',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#f0f0f0',
      borderWidth: 1,
      padding: [8, 12],
      textStyle: {
        fontSize: 12,
        color: 'rgba(0, 0, 0, 0.75)'
      },
      shadowColor: 'rgba(0, 0, 0, 0.05)',
      shadowBlur: 8,
      shadowOffsetX: 0,
      shadowOffsetY: 2
    },
    legend: {
      orient: 'vertical',
      left: '5%',
      top: 'center',
      itemWidth: 10,
      itemHeight: 10,
      textStyle: {
        fontSize: 12,
        color: 'rgba(0, 0, 0, 0.65)'
      },
      icon: 'circle'
    },
    series: [
      {
        name: '项目类型分布',
        type: 'pie',
        radius: ['45%', '75%'],
        center: ['65%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: 'rgba(255, 255, 255, 0.8)',
          borderWidth: 4
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          scale: false,  // 禁用缩放效果
          scaleSize: 0,  // 设置缩放大小为0
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold',
            color: 'rgba(0, 0, 0, 0.85)'
          },
          itemStyle: {
            borderWidth: 1,
            borderColor: 'rgba(255, 255, 255, 0.8)',
            shadowBlur: 0, 
            shadowColor: 'transparent',  // 设置阴影颜色为透明
            shadowOffsetX: 0,
            shadowOffsetY: 0
          }
        },
        labelLine: {
          show: false
        },
        data: pieData
      }
    ]
  };

  // 应用配置项
  pieChart.setOption(option);

  // 窗口大小调整监听
  window.addEventListener('resize', handleResize);
};

// 窗口大小调整
const handleResize = () => {
  if (trendChart) {
    trendChart.resize();
  }
  if (pieChart) {
    pieChart.resize();
  }
};

// 组件卸载前清理资源
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
  if (trendChart) {
    trendChart.dispose();
    trendChart = null;
  }
  if (pieChart) {
    pieChart.dispose();
    pieChart = null;
  }
});

// 页面加载时获取数据
onMounted(async () => {
  fetchStats();
  fetchRecentBuilds();
  fetchTodayBuilds();

  await Promise.all([
    fetchTrendData(),
    fetchDistributionData()
  ]);

  await nextTick();
  renderTrendChart();
  renderPieChart();
});
</script>

<style scoped>
.dashboard {
  /* padding: 16px; */
  color: rgba(0, 0, 0, 0.85); 
}

.card-content {
  text-align: center;
}

.card-content h2 {
  font-size: 18px;
  margin-bottom: 4px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.85);
}

.card-content p {
  margin: 0;
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
}

.card-subtitle {
  margin-top: 4px;
}

.success-text {
  color: #73d13d;
  font-weight: 500;
}

.failed-text {
  color: #ff7875;
  font-weight: 500;
}

.task-text {
  font-weight: 500;
}

.build-text {
  font-weight: 500;
}

.chart-row {
  margin-top: 12px;
}

.chart-container {
  height: 320px;
  width: 100%;
}

.recent-builds {
  margin-top: 12px;
}

.stat-cards .ant-card {
  height: 100%;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  box-shadow: none;
  transition: none;
}

.stat-cards .ant-card-head-title {
  font-size: 14px;
  font-weight: 700;
  color: rgba(0, 0, 0, 0.95);
}

:deep(.ant-table) {
  font-size: 13px;
}

:deep(.ant-table-thead > tr > th) {
  font-weight: 500;
  color: rgba(0, 0, 0, 0.65);
  font-size: 13px;
  background-color: rgba(0, 0, 0, 0.02);
}

:deep(.ant-table-tbody > tr > td) {
  color: rgba(0, 0, 0, 0.75);
}

:deep(.ant-table-tbody > tr:hover > td) {
  background-color: rgba(0, 0, 0, 0.02);
}

:deep(.ant-card-head-title) {
  font-size: 14px;
  font-weight: 700;
  color: rgba(0, 0, 0, 0.95);
}

:deep(.ant-card) {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  box-shadow: none;
  transition: none;
}

:deep(.ant-pagination-item-link) {
  font-size: 12px;
}

:deep(.ant-pagination-item) {
  font-size: 12px;
  min-width: 28px;
  height: 28px;
  line-height: 26px;
}

.status-text {
  font-weight: 400;
  font-size: 13px;
}

.status-success {
  color: #73d13d;
}
.status-failed {
  color: #ff7875; 
}
.status-running {
  color: #69c0ff; 
}
.status-pending {
  color: #ffc53d;
}
.status-terminated {
  color: rgba(0, 0, 0, 0.45);
}
</style>