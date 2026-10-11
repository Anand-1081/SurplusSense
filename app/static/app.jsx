/* SurplusSense UI: React + Material UI + Chart.js, compiled in the browser by Babel (no build step). */
const { useState, useEffect, useRef, useCallback, createContext, useContext } = React;
const {
  ThemeProvider, createTheme, CssBaseline, AppBar, Toolbar, Box, Container, Typography, Tabs, Tab, Card, CardContent,
  Grid, Button, TextField, MenuItem, FormControlLabel, Switch, Slider, Chip, Alert, Stack, LinearProgress,
  CircularProgress, Snackbar, Paper, Icon, Fade, Grow,
} = MaterialUI;

const GREEN = '#1F5F4A', LEAF = '#2E8B6A', AMBER = '#F2A33A', RED = '#C8553D', INK = '#17332B', MUTED = '#5B6B65';
Chart.defaults.font.family = 'Roboto, system-ui, sans-serif';
Chart.defaults.color = '#4a5f57';

/* ---------- theme: includes the button "press" animation ---------- */
const theme = createTheme({
  palette: {
    primary: { main: GREEN }, secondary: { main: AMBER, contrastText: INK },
    success: { main: LEAF }, error: { main: RED },
    background: { default: '#F4F7F2' }, text: { primary: INK },
  },
  shape: { borderRadius: 14 },
  typography: { fontFamily: 'Roboto, system-ui, sans-serif', button: { textTransform: 'none', fontWeight: 600 }, h6: { fontWeight: 700 } },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: {
          borderRadius: 12, padding: '8px 18px',
          transition: 'transform .12s ease, box-shadow .2s ease, background-color .2s ease',
          '&:hover': { transform: 'translateY(-2px)', boxShadow: '0 8px 18px rgba(31,95,74,.28)' },
          // pressed state: button sinks and squashes like a real click (MUI also adds the ripple)
          '&:active': { transform: 'translateY(1px) scale(.94)', boxShadow: '0 1px 2px rgba(0,0,0,.25) inset' },
          '&[aria-busy="true"]': { opacity: .85 },
        },
      },
    },
    MuiTab: { styleOverrides: { root: { textTransform: 'none', fontWeight: 600, minHeight: 56, transition: 'transform .12s ease', '&:active': { transform: 'scale(.95)' } } } },
    MuiCard: { styleOverrides: { root: { border: '1px solid #dbe5dd', boxShadow: '0 2px 12px rgba(23,51,43,.06)' } } },
  },
});

/* ---------- helpers ---------- */
const j = async (u, o) => {
  const r = await fetch(u, o);
  let d = null; try { d = await r.json(); } catch (e) { /* empty body */ }
  if (!r.ok) {
    const det = d && d.detail;
    const msg = Array.isArray(det) ? det.map(x => (x.loc ? x.loc[x.loc.length - 1] + ': ' : '') + x.msg).join('; ') : det;
    throw new Error(msg || 'Request failed (' + r.status + ')');
  }
  return d;
};
const post = (u, b) => j(u, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) });
const sign = n => (n > 0 ? '+' : '') + n;
const ToastCtx = createContext(() => {});

/* Button with a visible click effect: ripple + squash (theme) + spinner while the request is running */
function PressButton({ onClick, children, icon, variant = 'contained', ...props }) {
  const toast = useContext(ToastCtx);
  const [busy, setBusy] = useState(false);
  const run = async e => {
    if (busy) return;
    setBusy(true);
    try { await (onClick && onClick(e)); }
    catch (err) { toast(err.message || 'Something went wrong', 'error'); }
    finally { setBusy(false); }
  };
  return (
    <Button {...props} variant={variant} onClick={run} aria-busy={busy}
      startIcon={busy ? <CircularProgress size={16} color="inherit" /> : (icon ? <Icon fontSize="small">{icon}</Icon> : null)}>
      {children}
    </Button>
  );
}

function CountUp({ value, decimals = 0, suffix = '' }) {
  const [v, setV] = useState(0);
  const cur = useRef(0);
  useEffect(() => {
    const from = cur.current, to = Number(value) || 0, t0 = performance.now(); let raf;
    const step = t => {
      const p = Math.min(1, (t - t0) / 800), e = 1 - Math.pow(1 - p, 3);
      cur.current = from + (to - from) * e; setV(cur.current);
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return <>{v.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}{suffix}</>;
}

function StatTile({ icon, label, value, decimals = 0, suffix = '', text, color = GREEN, sub }) {
  return (
    <Paper variant="outlined" sx={{ p: 2, height: '100%', borderColor: '#d3e0d7', background: 'linear-gradient(180deg,#fff,#F1F7F3)', transition: 'transform .2s ease, box-shadow .2s ease', '&:hover': { transform: 'translateY(-3px)', boxShadow: '0 8px 20px rgba(23,51,43,.1)' } }}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ color: MUTED, mb: .5 }}>
        <Icon sx={{ color }} fontSize="small">{icon}</Icon><Typography variant="body2">{label}</Typography>
      </Stack>
      <Typography variant="h4" sx={{ fontWeight: 700, color }}>{text !== undefined ? text : <CountUp value={value} decimals={decimals} suffix={suffix} />}</Typography>
      {sub && <Typography variant="caption" sx={{ color: MUTED }}>{sub}</Typography>}
    </Paper>
  );
}

function Section({ title, icon, action, children, sx }) {
  return (
    <Card sx={sx}>
      <CardContent sx={{ p: { xs: 2, md: 3 } }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }} spacing={1}>
          <Stack direction="row" alignItems="center" spacing={1}>
            <Icon color="primary">{icon}</Icon><Typography variant="h6" color="primary">{title}</Typography>
          </Stack>
          {action}
        </Stack>
        {children}
      </CardContent>
    </Card>
  );
}

function ChartCanvas({ config, height = 300 }) {
  const ref = useRef(null);
  const key = JSON.stringify(config);
  useEffect(() => {
    const chart = new Chart(ref.current, config);
    return () => chart.destroy();
  }, [key]);
  return <Box sx={{ position: 'relative', height }}><canvas ref={ref} /></Box>;
}

function Empty({ children }) {
  return <Box sx={{ p: 3, textAlign: 'center', color: MUTED, border: '1px dashed #c5d4ca', borderRadius: 3 }}>{children}</Box>;
}

function DonorSelect({ donors, donorId, setDonorId, ...p }) {
  return (
    <TextField select size="small" label="Donor" value={donors.length ? donorId : ''} onChange={e => setDonorId(Number(e.target.value))} sx={{ minWidth: 220 }} {...p}>
      {donors.map(d => <MenuItem key={d.id} value={d.id}>{d.name}</MenuItem>)}
    </TextField>
  );
}

/* ================= TAB 1: FORECAST ================= */
function ForecastTab({ donors, donorId, setDonorId, setKg, goMatch }) {
  const toast = useContext(ToastCtx);
  const [meal, setMeal] = useState('lunch');
  const [prep, setPrep] = useState('150');
  const [rain, setRain] = useState(false);
  const [event, setEvent] = useState(false);
  const [res, setRes] = useState(null);
  const [week, setWeek] = useState(null);

  useEffect(() => {
    if (!donorId) return;
    setWeek(null); setRes(null);
    j('/api/forecast/week?donor_id=' + donorId).then(setWeek).catch(e => toast(e.message));
  }, [donorId]);
  useEffect(() => { if (week) setPrep(String(week.prepared_assumed[meal])); }, [week, meal]);

  const run = async () => {
    const f = await j('/api/forecast?donor_id=' + donorId + '&meal=' + meal + '&prepared=' + prep + '&rain=' + (+rain) + '&event=' + (+event));
    setRes(f); setKg(String(f.kg));
  };

  const weekCfg = week && {
    type: 'line',
    data: {
      labels: week.days.map(d => d.label),
      datasets: [
        { label: 'Low', data: week.days.map(d => d.low), borderColor: 'transparent', pointRadius: 0, tension: .35 },
        { label: 'Likely range (80%)', data: week.days.map(d => d.high), borderColor: 'transparent', backgroundColor: 'rgba(46,139,106,.2)', pointRadius: 0, fill: '-1', tension: .35 },
        { label: 'Forecast surplus (portions)', data: week.days.map(d => d.portions), borderColor: GREEN, backgroundColor: GREEN, borderWidth: 3, tension: .35, pointRadius: 5, pointHoverRadius: 8 },
      ],
    },
    options: {
      maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
      plugins: { legend: { labels: { usePointStyle: true, filter: i => i.datasetIndex !== 0 } }, tooltip: { filter: i => i.datasetIndex !== 0 } },
      scales: { y: { beginAtZero: true, title: { display: true, text: 'Portions left over (lunch + dinner)' } }, x: { grid: { display: false } } },
    },
  };

  return (
    <Grid container spacing={2.5}>
      <Grid item xs={12} md={5}>
        <Section title="Forecast surplus" icon="auto_graph" sx={{ height: '100%' }}>
          <Stack spacing={2}>
            <DonorSelect donors={donors} donorId={donorId} setDonorId={setDonorId} />
            <Stack direction="row" spacing={2}>
              <TextField select size="small" label="Meal" value={meal} onChange={e => setMeal(e.target.value)} sx={{ flex: 1 }}>
                <MenuItem value="lunch">Lunch</MenuItem><MenuItem value="dinner">Dinner</MenuItem>
              </TextField>
              <TextField size="small" type="number" label="Portions prepared" value={prep} onChange={e => setPrep(e.target.value)} inputProps={{ min: 1 }} sx={{ flex: 1 }} />
            </Stack>
            <Stack direction="row" spacing={2}>
              <FormControlLabel control={<Switch checked={rain} onChange={e => setRain(e.target.checked)} />} label="Rain" />
              <FormControlLabel control={<Switch checked={event} onChange={e => setEvent(e.target.checked)} />} label="Event nearby" />
            </Stack>
            <PressButton onClick={run} icon="insights" size="large">Run forecast</PressButton>
          </Stack>

          {res && (
            <Fade in timeout={500}><Box sx={{ mt: 3 }}>
              <Grid container spacing={1.5}>
                <Grid item xs={6}><StatTile icon="restaurant" label="Portions left over" value={res.portions} decimals={0} sub={'range ' + res.low + ' to ' + res.high} /></Grid>
                <Grid item xs={6}><StatTile icon="scale" label="Food to rescue" value={res.kg} decimals={1} suffix=" kg" color={AMBER} sub={res.kg_low + ' to ' + res.kg_high + ' kg'} /></Grid>
              </Grid>
              <Typography variant="body2" sx={{ mt: 2, mb: 1, color: MUTED }}>What the model says changes this number (what-if):</Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                <Chip icon={<Icon>water_drop</Icon>} label={'Rain: ' + sign(res.drivers.rain_effect) + ' portions'} color="primary" variant="outlined" />
                <Chip icon={<Icon>celebration</Icon>} label={'Event: ' + sign(res.drivers.event_effect) + ' portions'} color="secondary" variant="outlined" />
              </Stack>
              <PressButton onClick={goMatch} icon="arrow_forward" color="secondary" sx={{ mt: 2 }}>Find receivers for {res.kg} kg</PressButton>
            </Box></Fade>
          )}
        </Section>
      </Grid>

      <Grid item xs={12} md={7}>
        <Section title="Next 7 days: predicted surplus" icon="show_chart" sx={{ height: '100%' }}
          action={<Chip size="small" color="primary" icon={<Icon>auto_awesome</Icon>} label="ML forecast" />}>
          {week ? <>
            <ChartCanvas config={weekCfg} height={330} />
            <Typography variant="caption" sx={{ color: MUTED, display: 'block', mt: 1 }}>{week.note}</Typography>
          </> : <Box sx={{ py: 8, textAlign: 'center' }}><CircularProgress /></Box>}
        </Section>
      </Grid>
    </Grid>
  );
}

/* ================= TAB 2: REDISTRIBUTE ================= */
const STATUS_COLOR = { requested: 'warning', accepted: 'info', collected: 'success', declined: 'error' };

function MatchTab({ donors, donorId, setDonorId, kg, setKg, hours, setHours, tick, bump }) {
  const toast = useContext(ToastCtx);
  const [matches, setMatches] = useState(null);
  const [pickups, setPickups] = useState([]);

  useEffect(() => { j('/api/pickups').then(setPickups).catch(e => toast(e.message)); }, [tick]);

  const find = async () => {
    if (!(+kg > 0)) { toast('Enter the kg of food first, or run a forecast to fill it in', 'warning'); return; }
    const r = await post('/api/match', { donor_id: donorId, kg: +kg, hours_left: +hours });
    setMatches(r);
  };
  const request = async id => {
    await post('/api/pickups', { donor_id: donorId, kg: +kg, hours_left: +hours, receiver_id: id });
    toast('Pickup requested', 'success'); bump();
  };
  const setStatus = async (id, s) => { await fetch('/api/pickups/' + id + '/status/' + s, { method: 'POST' }); bump(); };

  return (
    <Grid container spacing={2.5}>
      <Grid item xs={12} md={6}>
        <Section title="Find the best receiver" icon="volunteer_activism" sx={{ height: '100%' }}>
          <Stack spacing={2}>
            <DonorSelect donors={donors} donorId={donorId} setDonorId={setDonorId} />
            <Stack direction="row" spacing={2}>
              <TextField size="small" type="number" label="Food to give (kg)" value={kg} onChange={e => setKg(e.target.value)} inputProps={{ min: 0.5, step: 0.5 }} sx={{ flex: 1 }} />
              <TextField size="small" type="number" label="Hours left (safe window)" value={hours} onChange={e => setHours(e.target.value)} inputProps={{ min: 0.5, max: 12, step: 0.5 }} sx={{ flex: 1 }} />
            </Stack>
            <PressButton onClick={find} icon="search" size="large">Find receivers</PressButton>
            <Typography variant="caption" sx={{ color: MUTED }}>Safe-window hours are entered by the donor; follow your food-safety guidance.</Typography>
          </Stack>
          <Box sx={{ mt: 2 }}>
            {matches === null ? null : matches.length === 0
              ? <Empty>No receiver can reach in time. Try a longer window or a smaller quantity.</Empty>
              : matches.map((m, i) => (
                <Grow in key={m.receiver_id} timeout={350 + i * 150}>
                  <Paper variant="outlined" sx={{ p: 2, mb: 1.5, borderColor: i === 0 ? LEAF : '#d3e0d7', borderWidth: i === 0 ? 2 : 1 }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1}>
                      <Box>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <Typography sx={{ fontWeight: 700 }}>{m.name}</Typography>
                          {i === 0 && <Chip size="small" color="success" label="Best match" icon={<Icon>star</Icon>} />}
                        </Stack>
                        <Typography variant="caption" sx={{ color: MUTED }}>{m.why}</Typography>
                      </Box>
                      <PressButton onClick={() => request(m.receiver_id)} color="secondary" size="small" icon="send">Request</PressButton>
                    </Stack>
                    <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mt: 1.5 }}>
                      <LinearProgress variant="determinate" value={Math.round(m.score * 100)} sx={{ flex: 1, height: 8, borderRadius: 4, bgcolor: '#E3EFE8', '& .MuiLinearProgress-bar': { borderRadius: 4, transition: 'transform .8s ease' } }} />
                      <Typography variant="body2" sx={{ fontWeight: 700, color: GREEN }}>{Math.round(m.score * 100)}%</Typography>
                    </Stack>
                  </Paper>
                </Grow>
              ))}
          </Box>
        </Section>
      </Grid>

      <Grid item xs={12} md={6}>
        <Section title="Pickups" icon="local_shipping" sx={{ height: '100%' }}>
          {pickups.length === 0 ? <Empty>No pickups yet. Request one from a matched receiver.</Empty> : pickups.map(p => (
            <Paper key={p.id} variant="outlined" sx={{ p: 1.5, mb: 1.2, borderColor: '#d3e0d7' }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1} flexWrap="wrap" useFlexGap>
                <Box>
                  <Typography sx={{ fontWeight: 600 }}>{p.donor} <Icon fontSize="inherit" sx={{ verticalAlign: 'middle', color: MUTED }}>east</Icon> {p.receiver}</Typography>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: .5 }}>
                    <Typography variant="caption" sx={{ color: MUTED }}>{p.kg} kg</Typography>
                    <Chip size="small" label={p.status} color={STATUS_COLOR[p.status] || 'default'} />
                  </Stack>
                </Box>
                <Stack direction="row" spacing={1}>
                  {p.status === 'requested' && <PressButton size="small" onClick={() => setStatus(p.id, 'accepted')} icon="check">Accept</PressButton>}
                  {p.status === 'requested' && <PressButton size="small" variant="outlined" color="error" onClick={() => setStatus(p.id, 'declined')}>Decline</PressButton>}
                  {(p.status === 'requested' || p.status === 'accepted') && <PressButton size="small" color="secondary" onClick={() => setStatus(p.id, 'collected')} icon="inventory_2">Collected</PressButton>}
                </Stack>
              </Stack>
            </Paper>
          ))}
        </Section>
      </Grid>
    </Grid>
  );
}

/* ================= TAB 3: IMPACT ================= */
function ImpactTab({ tick }) {
  const toast = useContext(ToastCtx);
  const [rate, setRate] = useState(50);
  const [series, setSeries] = useState(null);
  const [imp, setImp] = useState(null);
  const [pickups, setPickups] = useState([]);

  const loadSeries = r => j('/api/impact/series?rescue_rate=' + (r / 100)).then(setSeries).catch(e => toast(e.message));
  useEffect(() => {
    loadSeries(rate);
    j('/api/impact').then(setImp).catch(e => toast(e.message));
    j('/api/pickups').then(setPickups).catch(() => {});
  }, [tick]);

  const cfg = series && {
    type: 'line',
    data: {
      labels: series.labels,
      datasets: [
        { type: 'bar', label: 'Forecast surplus available (kg/day)', data: series.potential_kg, backgroundColor: 'rgba(46,139,106,.25)', borderRadius: 6, order: 3 },
        { label: 'Actual rescued (cumulative kg)', data: series.actual, borderColor: GREEN, backgroundColor: 'rgba(31,95,74,.15)', fill: true, borderWidth: 3, tension: .3, pointRadius: 4, order: 1 },
        { label: 'Projected rescued (AI forecast x rescue rate)', data: series.projected, borderColor: AMBER, backgroundColor: 'rgba(242,163,58,.18)', fill: true, borderDash: [8, 6], borderWidth: 3, tension: .3, pointRadius: 4, order: 2 },
      ],
    },
    options: {
      maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
      plugins: { legend: { labels: { usePointStyle: true } } },
      scales: { y: { beginAtZero: true, title: { display: true, text: 'kg of food' } }, x: { grid: { display: false } } },
    },
  };

  const statuses = ['requested', 'accepted', 'collected', 'declined'];
  const counts = statuses.map(s => pickups.filter(p => p.status === s).length);
  const donutCfg = {
    type: 'doughnut',
    data: { labels: statuses, datasets: [{ data: counts, backgroundColor: [AMBER, '#4C9BC9', LEAF, RED], borderWidth: 2, borderColor: '#fff' }] },
    options: { maintainAspectRatio: false, cutout: '62%', plugins: { legend: { position: 'bottom', labels: { usePointStyle: true } } } },
  };
  const s = series && series.summary;

  return (
    <Grid container spacing={2.5}>
      <Grid item xs={12}>
        <Grid container spacing={2}>
          <Grid item xs={6} md={3}><StatTile icon="eco" label="kg rescued" value={imp ? imp.kg_rescued : 0} decimals={1} /></Grid>
          <Grid item xs={6} md={3}><StatTile icon="ramen_dining" label="Meals (est.)" value={imp ? imp.meals_est : 0} color={AMBER} /></Grid>
          <Grid item xs={6} md={3}><StatTile icon="cloud_off" label="CO2e avoided kg (est.)" value={imp ? imp.co2e_kg_est : 0} decimals={1} color={LEAF} /></Grid>
          <Grid item xs={6} md={3}><StatTile icon="task_alt" label="Pickups done" text={imp ? imp.collected_pickups + ' / ' + imp.total_pickups : '0 / 0'} /></Grid>
        </Grid>
      </Grid>

      <Grid item xs={12} md={8}>
        <Section title="Impact: actual and forecast" icon="timeline" sx={{ height: '100%' }} action={<Chip size="small" color="primary" icon={<Icon>auto_awesome</Icon>} label="ML projection" />}>
          {series ? <>
            <ChartCanvas config={cfg} height={340} />
            <Box sx={{ mt: 2, px: 1 }}>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>Rescue rate assumption: {rate}% of forecast surplus gets collected</Typography>
              <Slider value={rate} min={0} max={100} step={5} valueLabelDisplay="auto" valueLabelFormat={v => v + '%'}
                onChange={(_, v) => setRate(v)} onChangeCommitted={(_, v) => loadSeries(v)}
                marks={[{ value: 25, label: '25%' }, { value: 50, label: '50%' }, { value: 75, label: '75%' }]} />
              <Typography variant="caption" sx={{ color: MUTED }}>
                {series.observed.rate === null ? 'No pickups recorded yet, so there is no measured rescue rate. ' : 'Pickups collected so far: ' + Math.round(series.observed.rate * 100) + '% of ' + series.observed.pickups + ' requested. '}
                {series.note}
              </Typography>
            </Box>
          </> : <Box sx={{ py: 10, textAlign: 'center' }}><CircularProgress /></Box>}
        </Section>
      </Grid>

      <Grid item xs={12} md={4}>
        <Stack spacing={2.5} sx={{ height: '100%' }}>
          <Section title={'Next ' + (s ? s.horizon_days : 7) + ' days (projected)'} icon="trending_up">
            <Stack spacing={1.5}>
              <StatTile icon="inventory" label="Surplus forecast" value={s ? s.potential_kg : 0} decimals={1} suffix=" kg" />
              <StatTile icon="ramen_dining" label="Meals if rescued (est.)" value={s ? s.meals_est : 0} color={AMBER} />
              <StatTile icon="cloud_off" label="CO2e avoided kg (est.)" value={s ? s.co2e_kg_est : 0} decimals={1} color={LEAF} />
            </Stack>
          </Section>
          <Section title="Pickup status" icon="donut_large">
            {pickups.length ? <ChartCanvas config={donutCfg} height={220} /> : <Empty>Pickups will appear here.</Empty>}
          </Section>
        </Stack>
      </Grid>
    </Grid>
  );
}

/* ================= TAB 4: MODEL ================= */
function ModelTab({ donors }) {
  const toast = useContext(ToastCtx);
  const [metrics, setMetrics] = useState(null);
  const [bt, setBt] = useState(null);
  const [imp, setImp] = useState(null);
  const [filter, setFilter] = useState('all');

  const loadAll = () => Promise.all([
    j('/api/metrics').then(setMetrics), j('/api/importance').then(setImp),
  ]).catch(e => toast(e.message));
  const loadBt = f => j('/api/backtest' + (f === 'all' ? '' : '?donor_id=' + f)).then(setBt).catch(e => toast(e.message));
  useEffect(() => { loadAll(); }, []);
  useEffect(() => { loadBt(filter); }, [filter]);

  const retrain = async () => { await post('/api/train', {}); await loadAll(); await loadBt(filter); toast('Model retrained', 'success'); };

  const btCfg = bt && {
    type: 'line',
    data: {
      labels: bt.map(d => d.day.slice(5)),
      datasets: [
        { label: 'Actual surplus', data: bt.map(d => d.actual), borderColor: INK, backgroundColor: INK, borderWidth: 2.5, tension: .25, pointRadius: 2 },
        { label: 'ML model', data: bt.map(d => d.pred), borderColor: LEAF, backgroundColor: LEAF, borderWidth: 2.5, tension: .25, pointRadius: 2 },
        { label: 'Simple baseline (same weekday average)', data: bt.map(d => d.baseline), borderColor: '#9AA8A1', backgroundColor: '#9AA8A1', borderDash: [6, 5], borderWidth: 2, tension: .25, pointRadius: 0 },
      ],
    },
    options: { maintainAspectRatio: false, interaction: { mode: 'index', intersect: false }, plugins: { legend: { labels: { usePointStyle: true } } },
      scales: { y: { beginAtZero: true, title: { display: true, text: 'Portions left over per day' } }, x: { grid: { display: false }, title: { display: true, text: 'Held-out test days (month-day)' } } } },
  };
  const impCfg = imp && {
    type: 'bar',
    data: { labels: imp.map(i => i.label), datasets: [{ data: imp.map(i => i.importance), backgroundColor: imp.map((_, k) => k === 0 ? GREEN : k === 1 ? LEAF : '#8CC3AC'), borderRadius: 6 }] },
    options: { indexAxis: 'y', maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => c.raw + '% of model signal' } } },
      scales: { x: { beginAtZero: true, max: 100, title: { display: true, text: '% importance (permutation, held-out data)' } }, y: { grid: { display: false } } } },
  };
  const better = metrics ? Math.round((1 - metrics.wape_model / metrics.wape_baseline) * 100) : 0;

  return (
    <Grid container spacing={2.5}>
      <Grid item xs={12}>
        <Grid container spacing={2}>
          <Grid item xs={6} md={3}><StatTile icon="model_training" label="Model error (WAPE)" value={metrics ? metrics.wape_model * 100 : 0} decimals={1} suffix="%" sub="lower is better" /></Grid>
          <Grid item xs={6} md={3}><StatTile icon="compare_arrows" label="Baseline error" value={metrics ? metrics.wape_baseline * 100 : 0} decimals={1} suffix="%" color="#7C8B84" sub="same-weekday average" /></Grid>
          <Grid item xs={6} md={3}><StatTile icon="trending_down" label="Error reduction" value={better} suffix="%" color={AMBER} sub="vs baseline" /></Grid>
          <Grid item xs={6} md={3}><StatTile icon="straighten" label="80% range coverage" value={metrics ? metrics.interval_coverage_80 * 100 : 0} decimals={0} suffix="%" color={LEAF} sub="target is 80%" /></Grid>
        </Grid>
      </Grid>

      <Grid item xs={12} md={7}>
        <Section title="Actual vs predicted (held-out days)" icon="query_stats" sx={{ height: '100%' }}
          action={<TextField select size="small" value={filter} onChange={e => setFilter(e.target.value)} sx={{ minWidth: 190 }}>
            <MenuItem value="all">All donors</MenuItem>
            {donors.map(d => <MenuItem key={d.id} value={d.id}>{d.name}</MenuItem>)}
          </TextField>}>
          {bt ? <ChartCanvas config={btCfg} height={320} /> : <Box sx={{ py: 8, textAlign: 'center' }}><CircularProgress /></Box>}
          <Typography variant="caption" sx={{ color: MUTED }}>These days were never used for training, so the gap between lines is honest out-of-sample error.</Typography>
        </Section>
      </Grid>

      <Grid item xs={12} md={5}>
        <Section title="What drives surplus?" icon="psychology" sx={{ height: '100%' }}>
          {imp ? <ChartCanvas config={impCfg} height={320} /> : <Box sx={{ py: 8, textAlign: 'center' }}><CircularProgress /></Box>}
        </Section>
      </Grid>

      <Grid item xs={12}>
        <Section title="About the model" icon="info">
          <Typography variant="body2" sx={{ mb: 2, color: MUTED }}>
            Gradient-boosted regression (scikit-learn) predicts leftover portions, plus two quantile models for the 80% range. Features: donor type, weekday, meal, portions prepared, rain, event and the last 7 logs' average surplus. {metrics && metrics.note}
          </Typography>
          <PressButton onClick={retrain} icon="refresh" color="secondary">Retrain model</PressButton>
        </Section>
      </Grid>
    </Grid>
  );
}

/* ================= APP SHELL ================= */
function App() {
  const [tab, setTab] = useState(0);
  const [donors, setDonors] = useState([]);
  const [donorId, setDonorId] = useState(1);
  const [kg, setKg] = useState('');
  const [hours, setHours] = useState('2');
  const [tick, setTick] = useState(0);
  const [snack, setSnack] = useState(null);
  const toast = useCallback((message, severity = 'error') => setSnack({ message, severity, k: Date.now() }), []);
  const bump = () => setTick(t => t + 1);

  useEffect(() => { j('/api/donors').then(d => { setDonors(d); if (d.length) setDonorId(d[0].id); }).catch(e => toast(e.message)); }, []);

  const shared = { donors, donorId, setDonorId };
  return (
    <ThemeProvider theme={theme}>
      <ToastCtx.Provider value={toast}>
        <CssBaseline />
        <AppBar position="static" elevation={0} sx={{ background: 'linear-gradient(135deg,#0F2A22 0%,' + GREEN + ' 100%)' }}>
          <Container maxWidth="lg">
            <Toolbar disableGutters sx={{ py: 1.5, gap: 2, flexWrap: 'wrap' }}>
              <a className="logo-link" href="/" style={{ display: 'flex', alignItems: 'center', gap: 14, textDecoration: 'none', color: '#fff' }}>
                <img className="logo-img" src="/static/logo.svg" width="52" height="52" alt="SurplusSense logo" />
                <Box>
                  <Typography variant="h5" sx={{ fontWeight: 700, lineHeight: 1.1 }}>Surplus<span style={{ color: AMBER }}>Sense</span></Typography>
                  <Typography variant="caption" sx={{ opacity: .85 }}>Predict surplus. Redistribute before it spoils.</Typography>
                </Box>
              </a>
              <Box sx={{ flexGrow: 1 }} />
              <Chip icon={<Icon sx={{ color: '#fff !important' }}>science</Icon>} label="Synthetic demo data" sx={{ color: '#fff', bgcolor: 'rgba(255,255,255,.15)' }} />
            </Toolbar>
            <Tabs value={tab} onChange={(_, v) => setTab(v)} textColor="inherit" indicatorColor="secondary" variant="scrollable" scrollButtons="auto">
              <Tab icon={<Icon>auto_graph</Icon>} iconPosition="start" label="Forecast" />
              <Tab icon={<Icon>volunteer_activism</Icon>} iconPosition="start" label="Redistribute" />
              <Tab icon={<Icon>eco</Icon>} iconPosition="start" label="Impact" />
              <Tab icon={<Icon>psychology</Icon>} iconPosition="start" label="Model" />
            </Tabs>
          </Container>
        </AppBar>

        <Container maxWidth="lg" sx={{ py: 3 }}>
          <Alert severity="warning" sx={{ mb: 2.5 }}>
            Prototype running on <b>synthetic demo data</b>. Accuracy shown here proves the code works, not real-world performance.
          </Alert>
          <Fade in key={tab} timeout={450}>
            <div>
              {tab === 0 && <ForecastTab {...shared} setKg={setKg} goMatch={() => setTab(1)} />}
              {tab === 1 && <MatchTab {...shared} kg={kg} setKg={setKg} hours={hours} setHours={setHours} tick={tick} bump={bump} />}
              {tab === 2 && <ImpactTab tick={tick} />}
              {tab === 3 && <ModelTab donors={donors} />}
            </div>
          </Fade>
          <Typography variant="caption" sx={{ display: 'block', textAlign: 'center', color: MUTED, mt: 4 }}>
            SurplusSense MVP. Meals and CO2e use placeholder conversion factors (see app/config.py).
          </Typography>
        </Container>

        {snack && (
          <Snackbar key={snack.k} open autoHideDuration={4000} onClose={() => setSnack(null)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
            <Alert severity={snack.severity} variant="filled" onClose={() => setSnack(null)}>{snack.message}</Alert>
          </Snackbar>
        )}
      </ToastCtx.Provider>
    </ThemeProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
