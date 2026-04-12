<template>
  <div class="app">
    <div v-if="detecting && detectionSteps.length" class="modal">
      <div class="modal-card">
        <div class="modal-head">
          <h3>算法对比进行中</h3>
          <div class="meta">
            <span>已完成 {{ completedSteps }}/{{ detectionSteps.length }} 步</span>
            <span>已用时 {{ elapsedSeconds }}s</span>
          </div>
        </div>
        <div class="bar"><div class="bar-fill" :style="{ width: progressPercent + '%' }"></div></div>
        <div class="step-list">
          <div v-for="(step, index) in detectionSteps" :key="step.title" class="step" :class="{ active: index === progressIndex, done: index < progressIndex }">
            <div class="badge">{{ index < progressIndex ? '✓' : index + 1 }}</div>
            <div>
              <div class="step-title">{{ step.title }}</div>
              <small>{{ step.detail }}</small>
            </div>
          </div>
        </div>
      </div>
    </div>

    <header class="hero hero-compact">
      <div class="hero-top">
        <div class="hero-kicker">Privacy-Aware Community Detection</div>
        <h1>隐私保护的多层网络社区检测</h1>
      </div>
      <p class="hero-desc">三栏布局：左侧参数 · 中间实验结果 · 右侧网络可视化。</p>
    </header>

    <div class="studio-layout">
      <aside class="panel config-panel">
        <div class="panel-head panel-head--tight">
          <div>
            <h2>实验配置</h2>
            <p class="panel-sub">数据、算法、进化优化</p>
          </div>
          <div class="panel-tag">Config</div>
        </div>

        <div class="config-scroll">
        <div class="config-block">
          <div class="block-title">数据</div>
          <div class="field">
            <label>数据源</label>
            <div class="row pill-row segmented-row">
              <label class="choice-pill">
                <input v-model="form.source_type" type="radio" value="builtin">
                <span class="choice-text">内置</span>
              </label>
              <label class="choice-pill">
                <input v-model="form.source_type" type="radio" value="upload">
                <span class="choice-text">上传</span>
              </label>
            </div>
          </div>

          <div v-if="form.source_type === 'builtin'" class="field">
            <label>数据集</label>
            <select v-model="form.dataset_name">
              <option v-for="dataset in builtinDatasets" :key="dataset.id" :value="dataset.id">{{ dataset.label }}</option>
            </select>
          </div>

          <template v-if="form.source_type === 'builtin' && form.dataset_name === 'biogrid'">
            <div class="field">
              <label>BioGRID 物种</label>
              <select v-model="form.biogrid_member" :disabled="!catalog.biogrid_species.length">
                <option v-for="sp in catalog.biogrid_species" :key="sp.member" :value="sp.member">
                  {{ sp.label }}
                </option>
              </select>
              <p v-if="!catalog.biogrid_species.length" class="hint-text hint-warn hint-text--micro">
                未检测到 tab3：将 <code>.zip</code> 或 <code>data/BIOGRID-ORGANISM-LATEST.tab3/</code> 放入 <code>data/</code> 后刷新。
              </p>
            </div>
            <details v-if="catalog.biogrid_species.length" class="config-details biogrid-adv">
              <summary>BioGRID：层数、边数与节点上限</summary>
              <div class="config-details-body biogrid-block">
                <div class="check-row check-row--lead">
                  <input id="biogrid-auto-layers" v-model="form.biogrid_auto_layers" type="checkbox">
                  <div class="check-copy">
                    <label for="biogrid-auto-layers" class="check-main">自动推断层数（约 82% 覆盖）</label>
                    <p class="check-sub">关闭后「层数」为固定取边数最多的前 N 个实验系统。</p>
                  </div>
                </div>
                <div class="grid compact-grid">
                  <div class="field">
                    <label>{{ form.biogrid_auto_layers ? '层数上限' : '层数' }}</label>
                    <input v-model.number="form.biogrid_top_layers" type="number" min="1" max="3" step="1">
                  </div>
                  <div class="field">
                    <label>min_edges</label>
                    <input v-model.number="form.biogrid_min_edges" type="number" min="1" step="1">
                  </div>
                  <div class="field full-span">
                    <label>max_nodes</label>
                    <input v-model.number="form.biogrid_max_nodes" type="number" min="20" step="10">
                  </div>
                  <div class="check-row check-row--tight full-span">
                    <input id="biogrid-include-genetic" v-model="form.biogrid_include_genetic" type="checkbox">
                    <label for="biogrid-include-genetic" class="check-main check-main--single">含 genetic 互作</label>
                  </div>
                </div>
              </div>
            </details>
          </template>

          <template v-if="form.source_type === 'builtin' && form.dataset_name === 'lfr'">
            <details class="config-details lfr-block" open>
              <summary>LFR 生成参数</summary>
              <div class="config-details-body">
                <div class="check-row check-row--lead">
                  <input id="lfr-custom-enabled" v-model="form.lfr_custom_enabled" type="checkbox">
                  <div class="check-copy">
                    <label for="lfr-custom-enabled" class="check-main">自定义参数</label>
                    <p class="check-sub">关闭时使用预设；开启后按 NetworkX <code>LFR_benchmark_graph</code> 手填。</p>
                  </div>
                </div>
                <div v-if="!form.lfr_custom_enabled" class="field">
                  <label>预设</label>
                  <select v-model="form.lfr_preset" :disabled="!catalog.lfr_presets.length">
                    <option v-for="p in catalog.lfr_presets" :key="p.id" :value="p.id">{{ p.label }}</option>
                  </select>
                  <p v-if="!catalog.lfr_presets.length" class="hint-text hint-text--micro">未加载预设列表，请确认后端已启动。</p>
                </div>
                <div v-else class="grid compact-grid">
                  <div class="field">
                    <label>N（节点数）</label>
                    <input v-model.number="form.lfr_n" type="number" min="10" step="1">
                  </div>
                  <div class="field">
                    <label>q（多层网络层数）</label>
                    <input v-model.number="form.lfr_multiplex_layers" type="number" min="1" max="32" step="1">
                  </div>
                  <div class="field">
                    <label>τ1（γ，度分布幂律指数）</label>
                    <input v-model.number="form.lfr_tau1" type="number" step="0.1" min="1.01">
                  </div>
                  <div class="field">
                    <label>τ2（β 近似，须 &gt;1）</label>
                    <input v-model.number="form.lfr_tau2" type="number" step="0.05" min="1.01">
                  </div>
                  <div class="field">
                    <label>μ（混合参数，实验中只调此项）</label>
                    <input v-model.number="form.lfr_mu" type="number" step="0.05" min="0" max="1">
                  </div>
                  <div class="field">
                    <label>⟨k⟩（average_degree）</label>
                    <input v-model.number="form.lfr_average_degree" type="number" min="1" step="1">
                  </div>
                  <div class="field">
                    <label>maxk（max_degree）</label>
                    <input v-model.number="form.lfr_max_degree" type="number" min="2" step="1">
                  </div>
                  <div class="field">
                    <label>min_community</label>
                    <input v-model.number="form.lfr_min_community" type="number" min="1" step="1">
                  </div>
                  <div class="field">
                    <label>max_community</label>
                    <input v-model.number="form.lfr_max_community" type="number" min="1" step="1">
                  </div>
                  <div class="field full-span">
                    <label>max_iters</label>
                    <input v-model.number="form.lfr_max_iters" type="number" min="100" step="100">
                  </div>
                </div>
              </div>
            </details>
          </template>

          <template v-if="form.source_type === 'builtin' && form.dataset_name === 'mlfr'">
            <details class="config-details mlfr-block" open>
              <summary>mLFR 生成参数</summary>
              <div class="config-details-body">
                <p class="hint-text hint-text--micro full-span">与后端 Java 生成器一致；层数 <code>l</code> 为多层网络层数。</p>
                <div class="grid compact-grid">
                  <div class="field">
                    <label>network_type</label>
                    <input v-model.trim="form.mlfr_network_type" type="text" maxlength="8" placeholder="UU">
                  </div>
                  <div class="field">
                    <label>n</label>
                    <input v-model.number="form.mlfr_n" type="number" min="10" step="1">
                  </div>
                  <div class="field">
                    <label>avg</label>
                    <input v-model.number="form.mlfr_avg" type="number" step="0.1" min="0.01">
                  </div>
                  <div class="field">
                    <label>max</label>
                    <input v-model.number="form.mlfr_max" type="number" min="1" step="1">
                  </div>
                  <div class="field">
                    <label>mix</label>
                    <input v-model.number="form.mlfr_mix" type="number" step="0.01" min="0" max="1">
                  </div>
                  <div class="field">
                    <label>tau1</label>
                    <input v-model.number="form.mlfr_tau1" type="number" step="0.1" min="1.01">
                  </div>
                  <div class="field">
                    <label>tau2</label>
                    <input v-model.number="form.mlfr_tau2" type="number" step="0.1" min="1.01">
                  </div>
                  <div class="field">
                    <label>mincom</label>
                    <input v-model.number="form.mlfr_mincom" type="number" min="1" step="1">
                  </div>
                  <div class="field">
                    <label>maxcom</label>
                    <input v-model.number="form.mlfr_maxcom" type="number" min="1" step="1">
                  </div>
                  <div class="field">
                    <label>l（层数）</label>
                    <input v-model.number="form.mlfr_l" type="number" min="1" max="32" step="1">
                  </div>
                  <div class="field">
                    <label>dc</label>
                    <input v-model.number="form.mlfr_dc" type="number" step="0.01">
                  </div>
                  <div class="field">
                    <label>rc</label>
                    <input v-model.number="form.mlfr_rc" type="number" step="0.01">
                  </div>
                  <div class="field">
                    <label>mparam1</label>
                    <input v-model.number="form.mlfr_mparam1" type="number" step="0.1" min="0.01">
                  </div>
                  <div class="field">
                    <label>on</label>
                    <input v-model.number="form.mlfr_on" type="number" min="0" step="1">
                  </div>
                  <div class="field">
                    <label>om</label>
                    <input v-model.number="form.mlfr_om" type="number" min="0" step="1">
                  </div>
                </div>
              </div>
            </details>
          </template>

          <div v-if="form.source_type === 'upload'" class="field">
            <label>上传文件</label>
            <input type="file" accept=".txt,.csv,.npy,.npz" @change="onFileSelect">
            <small v-if="uploadedFile">当前：{{ uploadedFile.name }}</small>
          </div>
        </div>

        <div class="config-block">
          <div class="block-title">算法（核心）</div>
          <div class="field">
            <label>算法</label>
            <select v-model="form.algorithm">
              <option v-for="algorithm in catalog.algorithms" :key="algorithm" :value="algorithm">{{ algorithm }}</option>
            </select>
          </div>
          <div class="grid compact-grid">
            <div class="field">
              <label>λ</label>
              <input v-model.number="form.lambd" type="number" step="0.01" min="0" @blur="normalizeCoreParams">
            </div>
            <div class="field">
              <label>ε</label>
              <input v-model.number="form.epsilon" type="number" step="0.01" min="0.1" @blur="normalizeCoreParams">
            </div>
          </div>
          <details class="config-details">
            <summary>更多：δ、密钥、随机种子</summary>
            <div class="config-details-body">
              <div class="grid compact-grid">
                <div class="field">
                  <label>delta</label>
                  <input v-model.number="form.delta" type="number" step="0.00001" @blur="normalizeCoreParams">
                </div>
                <div class="field">
                  <label>key_size</label>
                  <input v-model.number="form.key_size" type="number" step="128" min="128">
                </div>
                <div class="field full-span">
                  <label>random_state</label>
                  <input v-model.number="form.random_state" type="number">
                </div>
              </div>
            </div>
          </details>
        </div>

        <details class="config-details">
          <summary>展示：布局与全算法对比</summary>
          <div class="config-details-body">
            <div class="grid compact-grid">
              <div class="field full-span">
                <label>可视化布局</label>
                <select v-model="form.layout">
                  <option value="spring">spring</option>
                  <option value="circular">circular</option>
                  <option value="kamada_kawai">kamada_kawai</option>
                  <option value="3d_spring">3d_spring</option>
                  <option value="3d_interactive">3d_interactive</option>
                </select>
              </div>
              <div class="field full-span">
                <label>全算法对比</label>
                <select v-model="form.include_benchmark">
                  <option :value="true">true</option>
                  <option :value="false">false</option>
                </select>
              </div>
            </div>
          </div>
        </details>

        <details ref="eaDetails" class="config-details ea-block">
          <summary>遗传算法 · 手动优化</summary>
          <div class="config-details-body">
            <p class="hint-text hint-text--ea-one">搜索 ε、λ，评估≈种群×代数（同后端优化器）。</p>
            <div class="grid compact-grid ea-grid-tight">
              <div class="field">
                <label>种群</label>
                <input v-model.number="eaForm.population_size" type="number" min="2" max="40" step="1">
              </div>
              <div class="field">
                <label>代数</label>
                <input v-model.number="eaForm.generations" type="number" min="1" max="50" step="1">
              </div>
              <div class="field full-span ea-inline-toggles">
                <label class="ea-mini-check">
                  <input v-model="eaForm.compare_baseline" type="checkbox">
                  对照 ε、λ
                </label>
                <label class="ea-mini-check">
                  <input v-model="eaForm.save_json" type="checkbox">
                  保存 <code>output/*.json</code>
                </label>
              </div>
            </div>
            <div class="ea-actions">
              <button
                type="button"
                class="ea-run"
                :disabled="eaLoading || form.source_type === 'upload' || !eaCanRun"
                @click="runEaOptimize"
              >
                {{ eaLoading ? "进化中…" : "运行进化优化" }}
              </button>
              <span class="ea-meta">≈{{ eaEvaluations }} 次</span>
            </div>
            <p v-if="eaError" class="msg error msg--micro">{{ eaError }}</p>
            <div v-if="eaResult" class="ea-result-stack">
              <div class="ea-outcome ea-outcome--sidebar">
                <p v-if="eaResult.saved_path" class="hint-text hint-text--micro ea-saved-path" :title="eaResult.saved_path">已保存：{{ eaResult.saved_path }}</p>
                <div class="table-wrap ea-table-wrap ea-table-compact">
                  <table>
                    <thead>
                      <tr>
                        <th></th>
                        <th>fit</th>
                        <th>ε</th>
                        <th>λ</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-if="eaResult.baseline">
                        <td>对照</td>
                        <td>{{ formatMetric(eaResult.baseline.fitness) }}</td>
                        <td>{{ formatMetric(eaResult.baseline.params?.epsilon) }}</td>
                        <td>{{ formatMetric(eaResult.baseline.params?.lambd) }}</td>
                      </tr>
                      <tr class="ea-best-row">
                        <td>最优</td>
                        <td>{{ formatMetric(eaResult.best?.fitness) }}</td>
                        <td>{{ formatMetric(eaResult.best?.params?.epsilon) }}</td>
                        <td>{{ formatMetric(eaResult.best?.params?.lambd) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
              <details v-if="eaResult.history?.length" ref="eaChartFold" class="ea-chart-fold" @toggle="onEaChartFoldToggle">
                <summary>进化曲线</summary>
                <div ref="eaChart" class="ea-chart"></div>
              </details>
            </div>
          </div>
        </details>

        <div v-if="form.source_type === 'builtin'" class="field full-span auto-ea-row">
          <label class="ea-mini-check">
            <input v-model="form.auto_ea_before_detect" type="checkbox">
            检测前自动遗传优化并写回 <strong>ε、λ</strong>（预算上限 8×6）
          </label>
        </div>
        </div>

        <div class="config-footer">
          <div class="actions">
            <button :disabled="detecting || !canSubmit" @click="detectCommunities">{{ detecting ? '正在检测...' : '执行社区检测' }}</button>
            <button
              class="secondary"
              :disabled="visualizing || !canSubmit || !hasDetectionResult"
              :title="!hasDetectionResult ? '请先执行社区检测' : ''"
              @click="visualizeResults"
            >{{ visualizing ? '生成图像中...' : '生成可视化' }}</button>
          </div>
          <p class="action-tip">建议先检测再可视化。</p>

          <p v-if="error" class="msg error msg--compact">{{ error }}</p>
          <p v-if="success" class="msg success msg--compact">{{ success }}</p>
        </div>
      </aside>

      <main class="panel results-panel results-panel--center">
        <div class="panel-head panel-head--tight">
          <div>
            <h2>实验结果</h2>
            <p class="panel-sub">指标与对比</p>
          </div>
          <div class="panel-tag soft">Result</div>
        </div>

        <div v-if="resultSummary" class="stats-strip stats-strip--cols">
          <div class="metric-card">
            <div class="metric-label">数据集</div>
            <div class="metric-value metric-text">{{ resultSummary.dataset?.name || form.dataset_name }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">节点数</div>
            <div class="metric-value">{{ resultSummary.graph_info?.num_nodes ?? "N/A" }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">边数</div>
            <div class="metric-value">{{ resultSummary.graph_info?.num_edges ?? "N/A" }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">NMI</div>
            <div class="metric-value">{{ formatMetric(resultSummary.statistics?.nmi) }}</div>
          </div>
        </div>

        <div v-else class="results-empty">
          <span class="results-empty-title">暂无结果</span>
          <span class="results-empty-hint">完成左侧「社区检测」后显示指标。</span>
        </div>

        <div v-if="resultSummary" class="summary summary--compact">
          <p><strong>摘要</strong> {{ resultSummary.dataset?.summary }}</p>
        </div>

        <div v-if="benchmarkRows.length" class="table-wrap table-wrap--results">
          <table>
            <thead><tr><th>算法</th><th>Q</th><th>D</th><th>NMI</th><th>pr</th><th>#</th></tr></thead>
            <tbody>
              <tr v-for="row in benchmarkRows" :key="row.algorithm">
                <td>{{ row.algorithm }}</td>
                <td>{{ formatMetric(row.modularity) }}</td>
                <td>{{ formatMetric(row.module_density) }}</td>
                <td>{{ formatMetric(row.nmi) }}</td>
                <td>{{ formatMetric(row.privacy_rate) }}</td>
                <td>{{ row.num_communities }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </main>

      <aside class="panel viz-panel">
        <div class="panel-head panel-head--tight">
          <div>
            <h2>网络可视化</h2>
            <p class="panel-sub">静态图 / 3D 交互</p>
          </div>
          <div class="panel-tag viz-tag">View</div>
        </div>
        <div class="viz-box" :class="{ ready: visualizationImage || interactive3dData, 'interactive-ready': isInteractive3D }">
          <div v-if="visualizing" class="spinner"></div>
          <div v-else-if="isInteractive3D" ref="plot3d" class="plot3d"></div>
          <img v-else-if="visualizationImage" :src="visualizationImage" alt="Community Visualization">
          <div v-else class="placeholder empty-state empty-state--viz">
            <div class="empty-badge">图</div>
            <div class="empty-title">此处显示网络图</div>
            <p>执行检测后点击「生成可视化」。</p>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import Plotly from "plotly.js-dist-min";

export default {
  name: "App",
  data() {
    return {
      apiBase: "/api",
      catalog: { datasets: [], algorithms: [], lfr_presets: [], biogrid_species: [], defaults: {} },
      builtinDatasets: [],
      uploadedFile: null,
      detectionResults: null,
      visualizationImage: null,
      interactive3dData: null,
      detecting: false,
      visualizing: false,
      progressIndex: 0,
      progressValue: 0,
      progressTimer: null,
      elapsedTimer: null,
      progressStartedAt: 0,
      elapsedSeconds: 0,
      error: "",
      success: "",
      form: {
        source_type: "builtin",
        dataset_name: "karate",
        algorithm: "DH-Louvain",
        epsilon: 1.0,
        delta: 1e-5,
        key_size: 512,
        random_state: 42,
        lambd: 0.5,
        layout: "spring",
        include_benchmark: true,
        biogrid_member: "",
        biogrid_top_layers: 3,
        biogrid_min_edges: 12,
        biogrid_max_nodes: 300,
        biogrid_include_genetic: true,
        biogrid_auto_layers: true,
        auto_ea_before_detect: true,
        lfr_preset: "bench500",
        lfr_custom_enabled: false,
        lfr_n: 500,
        lfr_tau1: 2.0,
        lfr_tau2: 1.5,
        lfr_mu: 0.25,
        lfr_average_degree: 10,
        lfr_max_degree: 40,
        lfr_min_community: 20,
        lfr_max_community: 50,
        lfr_max_iters: 15000,
        lfr_multiplex_layers: 3,
        mlfr_network_type: "UU",
        mlfr_n: 40,
        mlfr_avg: 6.0,
        mlfr_max: 12,
        mlfr_mix: 0.1,
        mlfr_tau1: 2.5,
        mlfr_tau2: 1.5,
        mlfr_mincom: 10,
        mlfr_maxcom: 20,
        mlfr_l: 3,
        mlfr_dc: 0.0,
        mlfr_rc: 0.0,
        mlfr_mparam1: 2.0,
        mlfr_on: 0,
        mlfr_om: 0,
      },
      eaForm: {
        population_size: 8,
        generations: 6,
        compare_baseline: true,
        save_json: true,
      },
      eaLoading: false,
      eaError: "",
      eaResult: null,
    };
  },
  watch: {
    "form.dataset_name"(name) {
      if (name === "biogrid" && this.catalog.biogrid_species?.length && !this.form.biogrid_member) {
        this.form.biogrid_member = this.catalog.biogrid_species[0].member;
      }
      if (name === "lfr" && this.catalog.lfr_presets?.length) {
        const ids = this.catalog.lfr_presets.map((p) => p.id);
        if (!ids.includes(this.form.lfr_preset)) {
          this.form.lfr_preset = this.catalog.lfr_presets[0].id;
        }
      }
    },
  },
  computed: {
    canSubmit() {
      if (this.form.source_type === "upload") return !!this.uploadedFile;
      if (this.form.dataset_name === "biogrid" && !this.catalog.biogrid_species?.length) return false;
      return true;
    },
    hasDetectionResult() {
      return this.detectionResults != null;
    },
    detectionSteps() {
      const steps = [];
      if (this.form.auto_ea_before_detect && this.form.source_type === "builtin") {
        const { pop, gen, evals } = this.predetectEaBudget;
        steps.push({
          title: "遗传算法优化 ε、λ",
          detail: `预算 ${pop}×${gen}（约 ${evals} 次评估），此步最耗时，请等待；完成后写回 ε、λ 再继续检测。`,
        });
      }
      steps.push(
        { title: "装载数据集与实验参数", detail: this.form.source_type === "upload" ? "正在读取上传文件并构建多层网络。" : "正在读取内置数据集并整理层信息。" },
        { title: "执行目标算法", detail: `正在运行 ${this.form.algorithm} 并计算当前选择算法的指标。` },
      );
      if (this.form.include_benchmark) {
        steps.push({ title: "进行全算法对比", detail: "正在依次运行其余算法，生成对比表。" });
      }
      steps.push({ title: "整理结果并返回前端", detail: "正在汇总统计信息和可视化结果。" });
      return steps;
    },
    predetectEaBudget() {
      const pop = Math.min(Math.max(2, Number(this.eaForm.population_size) || 8), 8);
      const gen = Math.min(Math.max(1, Number(this.eaForm.generations) || 6), 6);
      return { pop, gen, evals: pop * gen };
    },
    completedSteps() {
      return this.detecting ? Math.min(this.progressIndex, this.detectionSteps.length) : this.detectionSteps.length;
    },
    progressPercent() {
      return this.detecting ? this.progressValue : 100;
    },
    isInteractive3D() {
      return this.form.layout === "3d_interactive" && !!this.interactive3dData;
    },
    resultSummary() {
      return this.detectionResults || this.interactive3dData;
    },
    benchmarkRows() {
      return this.detectionResults?.benchmark || [];
    },
    eaEvaluations() {
      const p = Number(this.eaForm.population_size) || 0;
      const g = Number(this.eaForm.generations) || 0;
      return p * g;
    },
    eaCanRun() {
      if (this.form.source_type !== "builtin") return false;
      if (this.form.dataset_name === "biogrid" && !this.catalog.biogrid_species?.length) return false;
      if (this.eaEvaluations < 2 || this.eaEvaluations > 250) return false;
      return true;
    },
  },
  methods: {
    async loadCatalog() {
      try {
        const response = await axios.get(`${this.apiBase}/datasets`);
        this.catalog = response.data;
        this.builtinDatasets = this.catalog.datasets.filter((item) => item.source === "builtin");
        if (this.catalog.defaults) {
          Object.assign(this.form, this.catalog.defaults);
        }
        this.$nextTick(() => this.normalizeCoreParams());
        if (this.catalog.biogrid_species?.length) {
          this.form.biogrid_member = this.catalog.biogrid_species[0].member;
        }
        if (this.catalog.lfr_presets?.length) {
          const ids = this.catalog.lfr_presets.map((p) => p.id);
          if (!ids.includes(this.form.lfr_preset)) {
            this.form.lfr_preset = this.catalog.lfr_presets[0].id;
          }
        }
      } catch (err) {
        this.error = "无法读取后端数据目录，请先启动 FastAPI 服务。";
      }
    },
    onFileSelect(event) {
      this.uploadedFile = event.target.files[0] || null;
      this.error = "";
      this.success = this.uploadedFile ? "文件已载入，准备开始实验。" : "";
    },
    formatMetric(value) {
      if (value === null || value === undefined || Number.isNaN(value)) return "N/A";
      return Number(value).toFixed(4);
    },
    normalizeCoreParams() {
      const q = (v, places) => {
        if (v === null || v === undefined || v === "") return undefined;
        const n = Number(v);
        if (!Number.isFinite(n)) return undefined;
        return Math.round(n * 10 ** places) / 10 ** places;
      };
      const e = q(this.form.epsilon, 4);
      const l = q(this.form.lambd, 4);
      const d = q(this.form.delta, 8);
      if (e !== undefined) this.form.epsilon = e;
      if (l !== undefined) this.form.lambd = l;
      if (d !== undefined) this.form.delta = d;
    },
    ensureEaPanelOpen() {
      const el = this.$refs.eaDetails;
      if (el && typeof el.open !== "undefined") el.open = true;
    },
    ensureEaChartFoldOpen() {
      this.$nextTick(() => {
        const fold = this.$refs.eaChartFold;
        if (fold && typeof fold.open !== "undefined") fold.open = true;
        this.$nextTick(() => this.renderEaChart());
      });
    },
    onEaChartFoldToggle(e) {
      if (e.target.open) {
        this.$nextTick(() => this.renderEaChart());
      }
    },
    buildEaPayload() {
      return JSON.parse(JSON.stringify(this.form));
    },
    renderEaChart() {
      const el = this.$refs.eaChart;
      const history = this.eaResult?.history;
      if (!el || !history?.length) return;
      const gen = history.map((row) => row.generation);
      const best = history.map((row) => row.best_fitness);
      const mean = history.map((row) => row.mean_fitness);
      Plotly.newPlot(
        el,
        [
          {
            type: "scatter",
            mode: "lines+markers",
            name: "最优 fitness",
            x: gen,
            y: best,
            line: { color: "#195c65", width: 2 },
            marker: { size: 6 },
          },
          {
            type: "scatter",
            mode: "lines+markers",
            name: "平均 fitness",
            x: gen,
            y: mean,
            line: { color: "#d8864b", width: 2 },
            marker: { size: 6 },
          },
        ],
        {
          margin: { l: 34, r: 8, t: 14, b: 22 },
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(255,255,255,0.75)",
          font: { color: "#213547", size: 9 },
          title: { text: "fitness", font: { size: 10 } },
          xaxis: { title: "代数", gridcolor: "rgba(33,53,71,0.08)" },
          yaxis: { title: "fitness", gridcolor: "rgba(33,53,71,0.08)" },
          legend: { orientation: "h", yanchor: "bottom", y: 1.02, x: 0 },
        },
        { responsive: true, displaylogo: false }
      );
    },
    async runEaOptimize(opts = {}) {
      const population_size = opts.population_size ?? this.eaForm.population_size;
      const generations = opts.generations ?? this.eaForm.generations;
      const compare_baseline = opts.compare_baseline ?? this.eaForm.compare_baseline;
      const save_json = opts.save_json ?? this.eaForm.save_json;
      const silent = opts.silent === true;
      const applyBestToForm = opts.applyBestToForm === true;
      const skipChartRender = opts.skipChartRender === true;

      if (this.$refs.eaChart) {
        try {
          Plotly.purge(this.$refs.eaChart);
        } catch (e) {
          /* noop */
        }
      }
      this.eaError = "";
      this.eaLoading = true;
      this.eaResult = null;
      if (!silent) {
        this.$nextTick(() => this.ensureEaPanelOpen());
      }
      try {
        const { data } = await axios.post(
          `${this.apiBase}/optimize/ea`,
          {
            form: this.buildEaPayload(),
            population_size,
            generations,
            compare_baseline,
            save_json,
          },
          {
            headers: { "Content-Type": "application/json" },
            timeout: 3600000,
          }
        );
        this.eaResult = data;
        if (applyBestToForm && data.best?.params) {
          const p = data.best.params;
          if (p.epsilon != null) this.form.epsilon = Number(p.epsilon);
          if (p.lambd != null) this.form.lambd = Number(p.lambd);
          this.normalizeCoreParams();
        }
        if (!silent) {
          this.success = "进化参数优化完成，可将最优 ε、λ 填回上方表单后继续检测。";
        }
        if (!skipChartRender && data.history?.length) {
          this.$nextTick(() => this.ensureEaChartFoldOpen());
        }
      } catch (err) {
        const detail = err.response?.data?.detail;
        this.eaError = "进化优化失败：" + (typeof detail === "string" ? detail : err.message || "未知错误");
        return false;
      } finally {
        this.eaLoading = false;
      }
      return true;
    },
    startProgress() {
      this.stopProgress();
      this.progressIndex = 0;
      this.progressValue = 8;
      this.elapsedSeconds = 0;
      this.progressStartedAt = Date.now();
      const totalSteps = this.detectionSteps.length || 1;
      this.progressTimer = window.setInterval(() => {
        const ceiling = this.form.include_benchmark ? 92 : 88;
        const increment = this.progressValue < 48 ? 3.6 : this.progressValue < 72 ? 2.1 : 0.9;
        this.progressValue = Math.min(ceiling, this.progressValue + increment);
        const nextStep = Math.min(
          totalSteps - 1,
          Math.floor((this.progressValue / Math.max(ceiling, 1)) * totalSteps)
        );
        this.progressIndex = Math.max(this.progressIndex, nextStep);
      }, 180);
      this.elapsedTimer = window.setInterval(() => {
        this.elapsedSeconds += 1;
      }, 1000);
    },
    async finishProgress() {
      const minimumDuration = this.form.include_benchmark ? 2400 : 1800;
      const elapsed = Date.now() - this.progressStartedAt;
      if (elapsed < minimumDuration) {
        await new Promise((resolve) => window.setTimeout(resolve, minimumDuration - elapsed));
      }
      this.progressIndex = Math.max(0, this.detectionSteps.length - 1);
      while (this.progressValue < 100) {
        this.progressValue = Math.min(100, this.progressValue + 6);
        await new Promise((resolve) => window.setTimeout(resolve, 45));
      }
      await new Promise((resolve) => window.setTimeout(resolve, 180));
    },
    stopProgress() {
      if (this.progressTimer) window.clearInterval(this.progressTimer);
      if (this.elapsedTimer) window.clearInterval(this.elapsedTimer);
      this.progressTimer = null;
      this.elapsedTimer = null;
    },
    clearVisualization() {
      if (this.visualizationImage) {
        URL.revokeObjectURL(this.visualizationImage);
        this.visualizationImage = null;
      }
      this.interactive3dData = null;
      if (this.$refs.plot3d) Plotly.purge(this.$refs.plot3d);
    },
    buildFormData() {
      const formData = new FormData();
      Object.entries(this.form).forEach(([key, value]) => {
        if (value === undefined || value === null) return;
        if (typeof value === "boolean") {
          formData.append(key, value ? "true" : "false");
        } else {
          formData.append(key, value);
        }
      });
      if (this.form.source_type === "upload" && this.uploadedFile) formData.append("file", this.uploadedFile);
      return formData;
    },
    async detectCommunities() {
      if (!this.canSubmit) {
        this.error = "请先选择内置数据集或上传文件。";
        return;
      }
      this.detecting = true;
      this.error = "";
      this.success = "";
      this.clearVisualization();
      this.startProgress();
      try {
        if (this.form.auto_ea_before_detect && this.form.source_type === "builtin" && this.eaCanRun) {
          const { pop, gen } = this.predetectEaBudget;
          const eaOk = await this.runEaOptimize({
            population_size: pop,
            generations: gen,
            compare_baseline: false,
            save_json: false,
            silent: true,
            applyBestToForm: true,
            skipChartRender: true,
          });
          if (eaOk === false) {
            this.error = this.eaError || "遗传优化失败，已中止社区检测。";
            this.stopProgress();
            this.progressIndex = 0;
            this.progressValue = 0;
            this.detecting = false;
            return;
          }
        }
        const response = await axios.post(`${this.apiBase}/detect`, this.buildFormData(), {
          headers: { "Content-Type": "multipart/form-data" },
          timeout: 3600000,
        });
        this.detectionResults = response.data;
        let msg = "社区检测完成。";
        if (this.form.auto_ea_before_detect && this.form.source_type === "builtin" && this.eaResult?.best?.params) {
          msg += " 已按检测前遗传优化得到的 ε、λ 运行。";
        }
        this.success = msg;
        if (this.form.auto_ea_before_detect && this.form.source_type === "builtin" && this.eaResult?.history?.length) {
          this.ensureEaPanelOpen();
        }
      } catch (err) {
        this.error = "检测失败：" + (err.response?.data?.detail || err.message);
      } finally {
        await this.finishProgress();
        this.stopProgress();
        this.detecting = false;
      }
    },
    renderInteractive3D() {
      if (!this.interactive3dData || !this.$refs.plot3d) return;
      const plot = this.interactive3dData.plot || {};
      if (plot.mode === "multilayer") {
        const nodes = plot.nodes || [];
        const intraEdges = plot.intra_edges || [];
        const interlayerEdges = plot.interlayer_edges || [];
        const layerNames = plot.layer_names || [];
        const layerPalette = ["#38bdf8", "#22c55e", "#f59e0b", "#a78bfa", "#fb7185", "#14b8a6"];
        const communityPalette = ["#5eead4", "#38bdf8", "#f59e0b", "#a78bfa", "#f97316", "#22c55e", "#fb7185", "#fde047"];

        const traces = layerNames.map((layerName, layerIndex) => {
          const layerEdges = intraEdges.filter((edge) => edge.layer_index === layerIndex);
          const x = [];
          const y = [];
          const z = [];
          layerEdges.forEach((edge) => {
            x.push(edge.source_pos[0], edge.target_pos[0], null);
            y.push(edge.source_pos[1], edge.target_pos[1], null);
            z.push(edge.source_pos[2], edge.target_pos[2], null);
          });
          return {
            type: "scatter3d",
            mode: "lines",
            name: `${layerName} 层内边`,
            x,
            y,
            z,
            hoverinfo: "none",
            line: { color: layerPalette[layerIndex % layerPalette.length], width: 3 },
          };
        });

        if (interlayerEdges.length) {
          const bridgeX = [];
          const bridgeY = [];
          const bridgeZ = [];
          interlayerEdges.forEach((edge) => {
            bridgeX.push(edge.source_pos[0], edge.target_pos[0], null);
            bridgeY.push(edge.source_pos[1], edge.target_pos[1], null);
            bridgeZ.push(edge.source_pos[2], edge.target_pos[2], null);
          });
          traces.push({
            type: "scatter3d",
            mode: "lines",
            name: "跨层映射",
            x: bridgeX,
            y: bridgeY,
            z: bridgeZ,
            hoverinfo: "none",
            line: { color: "rgba(148, 163, 184, 0.42)", width: 2 },
          });
        }

        traces.push({
          type: "scatter3d",
          mode: "markers",
          name: "节点",
          x: nodes.map((n) => n.x),
          y: nodes.map((n) => n.y),
          z: nodes.map((n) => n.z),
          customdata: nodes.map((n) => [n.node_id, n.layer_name, n.community, n.degree]),
          hovertemplate: "节点: %{customdata[0]}<br>层: %{customdata[1]}<br>社区: %{customdata[2]}<br>度数: %{customdata[3]}<extra></extra>",
          marker: {
            size: nodes.map((n) => Math.max(2.8, (n.size || 4) * 0.95)),
            color: nodes.map((n) => communityPalette[Math.abs(Number(n.community || 0)) % communityPalette.length]),
            opacity: 0.96,
            line: { color: "rgba(255,255,255,0.9)", width: 0.7 },
          },
        });

        const layerAnnotations = layerNames.map((layerName, layerIndex) => ({
          x: 0.02,
          y: 0.96 - layerIndex * 0.06,
          xref: "paper",
          yref: "paper",
          text: `L${layerIndex + 1} · ${layerName}`,
          showarrow: false,
          font: { size: 12, color: layerPalette[layerIndex % layerPalette.length] },
          bgcolor: "rgba(8,17,31,0.72)",
          bordercolor: "rgba(148,163,184,0.14)",
          borderwidth: 1,
          borderpad: 4,
        }));

        Plotly.newPlot(
          this.$refs.plot3d,
          traces,
          {
            margin: { l: 0, r: 0, t: 18, b: 0 },
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            showlegend: true,
            annotations: layerAnnotations,
            legend: {
              x: 0.99,
              y: 0.99,
              xanchor: "right",
              bgcolor: "rgba(10,16,28,0.62)",
              bordercolor: "rgba(148,163,184,0.18)",
              borderwidth: 1,
              font: { color: "#dbeafe", size: 11 },
            },
            hoverlabel: {
              bgcolor: "#0f172a",
              bordercolor: "#38bdf8",
              font: { color: "#f8fafc" },
            },
            scene: {
              bgcolor: "#08111f",
              xaxis: { visible: false, showbackground: false },
              yaxis: { visible: false, showbackground: false },
              zaxis: { visible: false, showbackground: false },
              camera: { eye: { x: 1.6, y: 1.45, z: 1.2 } },
            },
          },
          { responsive: true, displaylogo: false, scrollZoom: true }
        );
        return;
      }

      const nodes = plot.nodes || [];
      const edges = plot.edges || [];
      const palette = ["#5eead4", "#38bdf8", "#f59e0b", "#a78bfa", "#f97316", "#22c55e", "#fb7185", "#fde047"];
      const nodeCommunityMap = new Map(nodes.map((node) => [String(node.id), node.community]));
      const edgeBuckets = {
        intra: { x: [], y: [], z: [] },
        inter: { x: [], y: [], z: [] },
      };
      edges.forEach((edge) => {
        const sourceCommunity = nodeCommunityMap.get(String(edge.source));
        const targetCommunity = nodeCommunityMap.get(String(edge.target));
        const bucket = sourceCommunity === targetCommunity ? edgeBuckets.intra : edgeBuckets.inter;
        bucket.x.push(edge.source_pos[0], edge.target_pos[0], null);
        bucket.y.push(edge.source_pos[1], edge.target_pos[1], null);
        bucket.z.push(edge.source_pos[2], edge.target_pos[2], null);
      });
      const traces = [
        {
          type: "scatter3d",
          mode: "lines",
          name: "社区内连边",
          x: edgeBuckets.intra.x,
          y: edgeBuckets.intra.y,
          z: edgeBuckets.intra.z,
          hoverinfo: "none",
          line: { color: "rgba(34, 197, 94, 0.88)", width: 4 },
        },
        {
          type: "scatter3d",
          mode: "lines",
          name: "社区间连边",
          x: edgeBuckets.inter.x,
          y: edgeBuckets.inter.y,
          z: edgeBuckets.inter.z,
          hoverinfo: "none",
          line: { color: "rgba(248, 113, 113, 0.78)", width: 3 },
        },
        {
          type: "scatter3d",
          mode: "markers",
          name: "节点",
          x: nodes.map((n) => n.x),
          y: nodes.map((n) => n.y),
          z: nodes.map((n) => n.z),
          customdata: nodes.map((n) => [n.id, n.community, n.degree]),
          hovertemplate: "节点: %{customdata[0]}<br>社区: %{customdata[1]}<br>度数: %{customdata[2]}<extra></extra>",
          marker: {
            size: nodes.map((n) => Math.max(3.2, (n.size || 4) * 1.1)),
            color: nodes.map((n) => palette[Math.abs(Number(n.community || 0)) % palette.length]),
            opacity: 0.96,
            line: { color: "rgba(255,255,255,0.9)", width: 0.8 },
          },
        },
      ];
      Plotly.newPlot(
        this.$refs.plot3d,
        traces,
        {
          margin: { l: 0, r: 0, t: 18, b: 0 },
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          showlegend: true,
          legend: {
            x: 0.01,
            y: 0.99,
            bgcolor: "rgba(10,16,28,0.62)",
            bordercolor: "rgba(148,163,184,0.18)",
            borderwidth: 1,
            font: { color: "#dbeafe", size: 11 },
          },
          hoverlabel: {
            bgcolor: "#0f172a",
            bordercolor: "#38bdf8",
            font: { color: "#f8fafc" },
          },
          scene: {
            bgcolor: "#08111f",
            xaxis: { visible: false, showbackground: false },
            yaxis: { visible: false, showbackground: false },
            zaxis: { visible: false, showbackground: false },
            camera: { eye: { x: 1.55, y: 1.4, z: 1.15 } },
          },
        },
        { responsive: true, displaylogo: false, scrollZoom: true }
      );
    },
    async visualizeResults() {
      if (!this.canSubmit) {
        this.error = "请先选择内置数据集或上传文件。";
        return;
      }
      if (!this.detectionResults) {
        this.error = "请先执行社区检测，再生成可视化。";
        return;
      }
      this.visualizing = true;
      this.error = "";
      this.success = "";
      try {
        this.clearVisualization();
        if (this.form.layout === "3d_interactive") {
          const response = await axios.post(`${this.apiBase}/visualize3d`, this.buildFormData(), { headers: { "Content-Type": "multipart/form-data" } });
          this.interactive3dData = response.data;
          this.$nextTick(() => this.renderInteractive3D());
          this.success = "交互式 3D 网络图已生成。";
        } else {
          const response = await axios.post(`${this.apiBase}/visualize`, this.buildFormData(), { headers: { "Content-Type": "multipart/form-data" }, responseType: "blob" });
          this.visualizationImage = URL.createObjectURL(response.data);
          this.success = "可视化图像已生成。";
        }
      } catch (err) {
        this.error = "可视化失败：" + (err.response?.data?.detail || err.message);
      } finally {
        this.visualizing = false;
      }
    },
  },
  mounted() {
    this.loadCatalog();
  },
};
</script>

<style>
:root { --bg: linear-gradient(135deg, #efe9da 0%, #dce8f2 55%, #c8d7c8 100%); --panel: rgba(255,255,255,0.92); --line: rgba(33,53,71,0.12); --text: #213547; --muted: #5d7083; --primary: #195c65; --accent: #d8864b; --studio-col-h: calc(100vh - 176px); }
* { box-sizing: border-box; }
body { margin: 0; font-family: "Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; background: var(--bg); color: var(--text); }
.app { min-height: 100vh; padding: 16px 18px 24px; }
.hero,.panel { border-radius: 16px; background: var(--panel); box-shadow: 0 12px 32px rgba(34,51,70,0.1); }
.hero { max-width: 1680px; margin: 0 auto 14px; padding: 14px 20px; position: relative; overflow: hidden; }
.hero-compact .hero-top { display: flex; flex-wrap: wrap; align-items: baseline; gap: 10px 16px; }
.hero::after { content: ""; position: absolute; right: -30px; top: -40px; width: 160px; height: 160px; border-radius: 999px; background: radial-gradient(circle, rgba(25,92,101,0.1), rgba(25,92,101,0)); pointer-events: none; }
.hero-kicker { display: inline-flex; align-items: center; margin-bottom: 0; padding: 4px 10px; border-radius: 999px; background: rgba(25,92,101,0.08); color: var(--primary); font-size: 0.72rem; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; }
.hero h1 { margin: 0; font-size: clamp(1.25rem, 2vw, 1.65rem); line-height: 1.2; }
.hero-desc { margin: 8px 0 0; color: var(--muted); line-height: 1.45; font-size: 0.86rem; max-width: 900px; }
.studio-layout { max-width: 1680px; margin: 0 auto; display: grid; grid-template-columns: minmax(240px, 20%) minmax(320px, 1.12fr) minmax(280px, 0.88fr); gap: 14px; align-items: stretch; min-height: var(--studio-col-h); }
.config-panel {
  display: flex;
  flex-direction: column;
  height: var(--studio-col-h);
  min-height: var(--studio-col-h);
  max-height: var(--studio-col-h);
  overflow: hidden;
  position: sticky;
  top: 10px;
  align-self: start;
}
.config-scroll {
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding-bottom: 4px;
}
.config-footer {
  flex-shrink: 0;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid rgba(33, 53, 71, 0.1);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0) 0%, rgba(250, 252, 253, 0.98) 20%);
}
.config-footer .actions { margin-top: 0; }
.results-panel {
  height: var(--studio-col-h);
  min-height: var(--studio-col-h);
  max-height: var(--studio-col-h);
  overflow-x: hidden;
  overflow-y: auto;
  position: sticky;
  top: 10px;
  -webkit-overflow-scrolling: touch;
  display: flex;
  flex-direction: column;
}
.viz-panel {
  display: flex;
  flex-direction: column;
  height: var(--studio-col-h);
  min-height: var(--studio-col-h);
  max-height: var(--studio-col-h);
  padding: 14px 16px;
  min-width: 0;
}
.panel { padding: 14px 16px; position: relative; overflow: hidden; }
.panel::before { content: ""; position: absolute; inset: 0 0 auto 0; height: 3px; background: linear-gradient(90deg, rgba(25,92,101,0.9), rgba(216,134,75,0.55)); opacity: 0.5; }
.panel.results-panel--center::before { background: linear-gradient(90deg, rgba(216,134,75,0.65), rgba(25,92,101,0.75)); opacity: 0.55; }
.viz-panel::before { background: linear-gradient(90deg, rgba(14,116,144,0.75), rgba(25,92,101,0.55)); }
.panel-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 14px; flex-shrink: 0; }
.panel-head--tight { margin-bottom: 8px; }
.panel-head h2 { margin: 0 0 2px; font-size: 1.05rem; }
.panel-sub { margin: 0; color: var(--muted); line-height: 1.35; font-size: 0.8rem; }
.panel-tag.viz-tag { background: linear-gradient(135deg, rgba(14,116,144,0.18), rgba(25,92,101,0.1)); color: #0e7490; }
.panel-tag { flex-shrink: 0; padding: 7px 12px; border-radius: 999px; background: linear-gradient(135deg, rgba(25,92,101,0.14), rgba(43,123,133,0.12)); color: var(--primary); font-size: 0.8rem; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; }
.panel-tag.soft { background: linear-gradient(135deg, rgba(216,134,75,0.16), rgba(216,134,75,0.08)); color: #ab5e2d; }
.config-block { border: 1px solid var(--line); border-radius: 10px; background: rgba(255,255,255,0.72); padding: 8px 10px; }
.config-block + .config-block { margin-top: 8px; }
.config-details {
  margin-top: 8px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(255,255,255,0.68);
}
.config-details > summary {
  cursor: pointer;
  padding: 6px 9px;
  font-size: 0.76rem;
  font-weight: 800;
  color: var(--primary);
  list-style: none;
  user-select: none;
  line-height: 1.35;
}
.config-details > summary::-webkit-details-marker { display: none; }
.config-details[open] > summary { border-bottom: 1px solid rgba(33,53,71,0.08); }
.config-details-body { padding: 6px 8px 8px; }
.config-details-body .field { margin-bottom: 8px; }
.config-details + .config-details { margin-top: 6px; }
.hint-text--micro { margin: 4px 0 0; font-size: 0.72rem; line-height: 1.4; }
.msg--micro { margin-top: 6px; padding: 6px 8px; font-size: 0.78rem; border-radius: 8px; }
.config-panel .field { margin-bottom: 8px; gap: 3px; }
.config-panel .field label { font-size: 0.82rem; }
.config-panel .field input,.config-panel .field select { min-height: 36px; border-radius: 10px; padding: 6px 10px; font-size: 0.88rem; }
.config-panel .choice-pill { min-height: 40px; padding: 0 12px; border-radius: 12px; font-size: 0.86rem; }
.config-panel .block-title { margin-bottom: 8px; font-size: 0.86rem; }
.hint-text--tight { margin: 4px 0 8px; font-size: 0.78rem; line-height: 1.45; }
.biogrid-adv { margin-top: 6px; }
.biogrid-block { margin-top: 0; }
.hint-text { margin: 8px 0 0; font-size: 0.86rem; line-height: 1.55; color: var(--muted); }
.hint-warn { color: #8a4b16; }
.hint-text code { font-size: 0.84em; padding: 1px 6px; border-radius: 6px; background: rgba(25,92,101,0.08); }
.biogrid-block .check-row {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(33, 53, 71, 0.1);
  background: rgba(25, 92, 101, 0.04);
  margin-bottom: 8px;
}
.biogrid-block .check-row--lead { margin-top: 2px; }
.biogrid-block .check-row--tight {
  padding: 10px 12px;
  margin-bottom: 0;
  background: rgba(255, 255, 255, 0.55);
}
.biogrid-block .check-row input[type="checkbox"] {
  width: 1.05rem;
  height: 1.05rem;
  min-width: 1.05rem;
  min-height: 1.05rem !important;
  margin: 2px 0 0;
  padding: 0;
  flex-shrink: 0;
  accent-color: #195c65;
  cursor: pointer;
  border-radius: 4px;
  align-self: flex-start;
}
.biogrid-block .check-copy { flex: 1; min-width: 0; }
.biogrid-block .check-main {
  display: block;
  font-size: 0.82rem;
  font-weight: 700;
  color: #274056;
  line-height: 1.3;
  cursor: pointer;
  margin: 0;
}
.biogrid-block .check-main--single { padding-top: 1px; line-height: 1.4; }
.biogrid-block .check-sub {
  margin: 4px 0 0;
  font-size: 0.72rem;
  line-height: 1.4;
  color: var(--muted);
  font-weight: 400;
}
.ea-block { margin-top: 0; }
.auto-ea-row { margin-top: 6px !important; margin-bottom: 4px !important; }
.ea-block code { font-size: 0.84em; padding: 1px 5px; border-radius: 6px; background: rgba(25,92,101,0.08); }
.ea-inline-toggles { flex-direction: column; gap: 6px; align-items: flex-start !important; }
.ea-mini-check {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 8px;
  font-size: 0.78rem;
  font-weight: 600;
  color: #274056;
  cursor: pointer;
  line-height: 1.35;
}
.field .ea-mini-check input[type="checkbox"] {
  width: 1.05rem !important;
  height: 1.05rem !important;
  min-height: 1.05rem !important;
  padding: 0 !important;
  margin-top: 2px;
  flex-shrink: 0;
  accent-color: #195c65;
  border-radius: 4px;
}
.ea-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 4px; }
.ea-run {
  min-height: 40px;
  padding: 0 14px;
  border-radius: 12px;
  font-size: 0.86rem;
  font-weight: 800;
  cursor: pointer;
  border: none;
  color: white;
  background: linear-gradient(135deg, #1a4d6e, #195c65);
}
.ea-run:disabled { opacity: 0.5; cursor: not-allowed; }
.ea-meta { font-size: 0.72rem; color: var(--muted); line-height: 1.3; max-width: 11rem; }
.ea-result-stack { margin-top: 6px; display: flex; flex-direction: column; gap: 6px; }
.ea-outcome { margin-top: 0; }
.ea-outcome--sidebar {
  max-height: 120px;
  overflow-x: hidden;
  overflow-y: auto;
  padding-right: 2px;
  -webkit-overflow-scrolling: touch;
}
.hint-text--ea-one { margin: 0 0 6px; font-size: 0.72rem; line-height: 1.35; color: var(--muted); }
.ea-grid-tight .field { margin-bottom: 5px !important; }
.ea-saved-path { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ea-table-wrap { margin-top: 4px; font-size: 0.68rem; overflow-x: auto; -webkit-overflow-scrolling: touch; }
.ea-table-compact table { min-width: 0; width: 100%; }
.ea-table-compact th, .ea-table-compact td { padding: 3px 4px; text-align: center; }
.ea-table-compact th:first-child, .ea-table-compact td:first-child { text-align: left; padding-left: 2px; }
.ea-table-wrap th, .ea-table-wrap td { padding: 4px 3px; white-space: nowrap; }
.ea-best-row { background: rgba(25, 92, 101, 0.07); font-weight: 700; }
.ea-chart-fold { margin-top: 4px; border: 1px solid rgba(33,53,71,0.1); border-radius: 8px; background: rgba(255,255,255,0.55); }
.ea-chart-fold > summary {
  cursor: pointer;
  padding: 5px 8px;
  font-size: 0.72rem;
  font-weight: 800;
  color: var(--primary);
  list-style: none;
  user-select: none;
}
.ea-chart-fold > summary::-webkit-details-marker { display: none; }
.ea-chart-fold[open] > summary { border-bottom: 1px solid rgba(33,53,71,0.06); }
.ea-chart {
  width: 100%;
  height: 104px;
  margin: 0;
  border-radius: 0 0 6px 6px;
  border: none;
  overflow: hidden;
  background: rgba(255,255,255,0.5);
}
.block-title { margin-bottom: 12px; color: var(--primary); font-size: 0.95rem; font-weight: 800; letter-spacing: 0.02em; }
.section + .section { margin-top: 22px; padding-top: 22px; border-top: 1px solid var(--line); }
.field { display: flex; flex-direction: column; gap: 8px; margin-bottom: 14px; }
.field:last-child { margin-bottom: 0; }
.field label { font-size: 0.92rem; font-weight: 700; color: #274056; }
.field input,.field select { width: 100%; min-width: 0; min-height: 46px; border-radius: 14px; border: 1px solid var(--line); background: rgba(255,255,255,0.96); padding: 10px 12px; font-size: 0.97rem; }
.config-panel .grid { gap: 8px; }
.field input:focus,.field select:focus { outline: none; border-color: rgba(25,92,101,0.35); box-shadow: 0 0 0 4px rgba(25,92,101,0.08); }
.row { display: flex; gap: 12px; flex-wrap: wrap; }
.pill-row { gap: 10px; }
.segmented-row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.choice-pill { display: inline-flex; align-items: center; justify-content: center; gap: 12px; min-height: 54px; padding: 0 18px; border-radius: 18px; border: 1px solid rgba(25,92,101,0.12); background: rgba(25,92,101,0.06); font-weight: 700; white-space: nowrap; transition: all 0.2s ease; }
.choice-pill:has(input:checked) { background: linear-gradient(135deg, rgba(25,92,101,0.14), rgba(43,123,133,0.08)); border-color: rgba(25,92,101,0.26); box-shadow: inset 0 0 0 1px rgba(25,92,101,0.06); }
.choice-pill input { margin: 0; width: 20px; height: 20px; flex-shrink: 0; accent-color: #1976d2; }
.choice-text { display: inline-flex; align-items: center; min-height: 20px; line-height: 1; white-space: nowrap; }
.grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.compact-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); align-items: end; }
.compact-grid .field { min-width: 0; }
.full-span { grid-column: 1 / -1; }
.upload-box,.summary,.table-wrap,.viz-box,.modal-card { border: 1px solid var(--line); background: rgba(255,255,255,0.82); }
.upload-box,.summary { border-radius: 18px; padding: 18px; }
.actions { display: grid; grid-template-columns: 1fr; gap: 8px; margin-top: 12px; }
.config-panel .actions button { min-height: 40px; border-radius: 12px; font-size: 0.88rem; padding: 0 12px; }
.action-tip { margin: 8px 2px 0; color: var(--muted); font-size: 0.78rem; line-height: 1.45; }
button { min-height: 52px; border: none; border-radius: 16px; padding: 0 16px; font-size: 0.98rem; font-weight: 800; cursor: pointer; background: linear-gradient(135deg, var(--primary), #2b7b85); color: white; }
button.secondary { background: linear-gradient(135deg, var(--accent), #c66e3b); }
button:disabled { opacity: 0.55; cursor: not-allowed; }
.msg { margin-top: 14px; padding: 14px 16px; border-radius: 14px; }
.msg--compact { margin-top: 8px; padding: 8px 10px; font-size: 0.82rem; line-height: 1.45; border-radius: 10px; }
.error { background: #fde9e6; color: #9a2f25; }
.success { background: #e7f3ed; color: #1c6a41; }
.stats-strip { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 12px; margin-bottom: 16px; }
.stats-strip--cols { grid-template-columns: repeat(2, minmax(0,1fr)); gap: 8px; margin-bottom: 10px; }
.metric-card { padding: 16px; border-radius: 18px; background: linear-gradient(150deg, #194e57, #2c7580); color: white; min-height: 100px; }
.results-panel .metric-card { padding: 10px 10px; border-radius: 12px; min-height: 0; }
.results-panel .metric-label { font-size: 0.72rem; margin-bottom: 4px; }
.results-panel .metric-value { font-size: 1.05rem; }
.results-panel .metric-text { font-size: 0.78rem; line-height: 1.25; word-break: break-all; }
.metric-label { opacity: 0.8; font-size: 0.88rem; margin-bottom: 8px; }
.metric-value { font-size: 1.5rem; font-weight: 800; }
.metric-text { font-size: 1rem; line-height: 1.35; }
.results-empty { padding: 16px 12px; border-radius: 12px; border: 1px dashed rgba(33,53,71,0.18); background: rgba(255,255,255,0.5); text-align: center; }
.results-panel .results-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 8rem; }
.results-empty-title { display: block; font-weight: 800; font-size: 0.88rem; color: #274056; margin-bottom: 4px; }
.results-empty-hint { font-size: 0.78rem; color: var(--muted); line-height: 1.4; }
.summary--compact { margin-top: 0; margin-bottom: 10px; padding: 8px 10px; border-radius: 10px; font-size: 0.78rem; line-height: 1.45; }
.summary--compact p { margin: 0; }
.table-wrap { margin-top: 18px; overflow-x: auto; border-radius: 18px; }
.table-wrap--results { margin-top: 8px; border-radius: 10px; }
table { width: 100%; border-collapse: collapse; min-width: 680px; }
.results-panel table { min-width: 0; font-size: 0.76rem; }
.results-panel th,.results-panel td { padding: 6px 5px; }
th,td { padding: 14px 14px; text-align: left; border-bottom: 1px solid var(--line); }
th { background: rgba(25,92,101,0.06); color: #284055; }
.viz-box { flex: 1; margin-top: 0; border-radius: 14px; min-height: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; overflow: hidden; background: linear-gradient(180deg, rgba(255,255,255,0.82), rgba(245,249,251,0.94)); }
.viz-panel .viz-box.ready { min-height: 0; }
.viz-box.interactive-ready {
  align-items: stretch;
  justify-content: flex-start;
  background: linear-gradient(180deg, #0d1726, #08111f);
  border-color: rgba(56,189,248,0.14);
  box-shadow: inset 0 0 0 1px rgba(148,163,184,0.08);
}
.viz-box img { width: 100%; max-width: 100%; max-height: 100%; height: auto; object-fit: contain; }
.viz-panel .plot3d { width: 100%; flex: 1; min-height: 200px; height: 100%; align-self: stretch; }
.spinner { width: 40px; height: 40px; border: 3px solid rgba(25,92,101,0.15); border-top-color: var(--primary); border-radius: 50%; animation: vizspin 0.75s linear infinite; }
@keyframes vizspin { to { transform: rotate(360deg); } }
.placeholder { color: var(--muted); }
.empty-state { text-align: center; max-width: 460px; padding: 32px 20px; }
.empty-state--viz { padding: 20px 16px; max-width: 320px; }
.empty-state--viz .empty-badge { width: 48px; height: 48px; margin-bottom: 10px; border-radius: 14px; font-size: 1.1rem; }
.empty-state--viz .empty-title { font-size: 0.95rem; margin-bottom: 6px; }
.empty-state--viz p { font-size: 0.82rem; line-height: 1.5; }
.empty-badge { width: 64px; height: 64px; margin: 0 auto 18px; border-radius: 20px; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, rgba(25,92,101,0.16), rgba(216,134,75,0.16)); color: var(--primary); font-size: 1.3rem; font-weight: 800; }
.empty-title { margin-bottom: 10px; color: var(--text); font-size: 1.08rem; font-weight: 800; }
.empty-state p { margin: 0; line-height: 1.75; }
.empty-preview { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 12px; width: 100%; margin-top: 24px; text-align: left; }
.preview-card { padding: 14px; border-radius: 16px; background: rgba(255,255,255,0.76); border: 1px solid rgba(33,53,71,0.08); box-shadow: 0 8px 20px rgba(34,51,70,0.06); }
.preview-title { margin-bottom: 6px; color: var(--text); font-weight: 800; }
.preview-card small { color: var(--muted); line-height: 1.6; }
.modal { position: fixed; inset: 0; z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 20px; background: rgba(16,27,33,0.34); backdrop-filter: blur(6px); }
.modal-card { width: min(720px,100%); padding: 24px; border-radius: 24px; box-shadow: 0 28px 70px rgba(18,43,49,0.22); }
.modal-head,.progress-head,.meta { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.meta span { padding: 6px 10px; border-radius: 999px; background: rgba(25,92,101,0.1); color: var(--primary); font-size: 0.88rem; font-weight: 700; }
.bar { width: 100%; height: 10px; border-radius: 999px; background: rgba(93,112,131,0.12); overflow: hidden; margin: 16px 0; }
.bar-fill { height: 100%; background: linear-gradient(90deg, #195c65, #d8864b); position: relative; }
.bar-fill::after { content: ""; position: absolute; inset: 0; background: linear-gradient(120deg, rgba(255,255,255,0) 20%, rgba(255,255,255,0.35) 50%, rgba(255,255,255,0) 80%); transform: translateX(-100%); animation: shine 1.4s linear infinite; }
.step-list { display: grid; gap: 10px; }
.step { display: grid; grid-template-columns: 28px 1fr; gap: 10px; padding: 10px 12px; border-radius: 14px; }
.step.active { background: rgba(25,92,101,0.08); }
.step.done { background: rgba(28,106,65,0.06); }
.badge { width: 28px; height: 28px; border-radius: 999px; display: flex; align-items: center; justify-content: center; font-weight: 700; background: rgba(93,112,131,0.12); }
.step.active .badge { background: linear-gradient(135deg, var(--primary), #2b7b85); color: white; }
.step-title { font-weight: 700; }
@keyframes shine { to { transform: translateX(100%); } }
@media (max-width: 1280px) {
  .studio-layout { grid-template-columns: minmax(220px, 24%) minmax(0, 1.08fr) minmax(240px, 0.92fr); gap: 12px; }
}
@media (max-width: 1100px) {
  .studio-layout { grid-template-columns: 1fr 1fr; grid-template-rows: auto auto; }
  .viz-panel {
    grid-column: 1 / -1;
    order: -1;
    height: auto;
    min-height: min(520px, 70vh);
    max-height: none;
  }
  .config-panel,.results-panel {
    height: auto;
    min-height: min(420px, 65vh);
    max-height: 70vh;
    position: static;
    overflow: hidden;
  }
  .config-scroll {
    flex: 1 1 auto;
    max-height: min(52vh, 440px);
  }
}
@media (max-width: 720px) {
  .studio-layout { grid-template-columns: 1fr; }
  .viz-panel { order: -1; height: auto; min-height: 360px; max-height: none; }
  .config-panel,.results-panel { height: auto; min-height: 0; max-height: none; }
  .config-scroll { max-height: 58vh; }
  .app { padding: 12px; }
  .grid,.compact-grid,.actions,.stats-strip,.stats-strip--cols,.empty-preview,.segmented-row { grid-template-columns: 1fr; }
  .choice-pill { width: 100%; justify-content: flex-start; }
  .hero,.panel { border-radius: 14px; }
}
</style>
