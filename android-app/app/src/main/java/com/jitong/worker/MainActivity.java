package com.jitong.worker;

import android.Manifest;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.text.InputType;
import android.util.Base64;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.google.zxing.integration.android.IntentIntegrator;
import com.google.zxing.integration.android.IntentResult;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.security.cert.Certificate;
import java.security.cert.CertificateFactory;
import java.text.DecimalFormat;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TimeZone;

import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManagerFactory;

public class MainActivity extends AppCompatActivity {

    private static final String PREFS = "jitong_worker";
    private static final String K_IP = "server_ip";
    private static final String K_CA = "ca_b64";
    private static final String K_TOKEN = "token";
    private static final String K_NAME = "employee_name";
    private static final String K_NO = "employee_no";
    private static final String K_ID = "employee_id";
    private static final String K_IS_ADMIN = "is_admin";
    private static final String K_JOBS = "jobs_json";
    private static final int REQ_CAMERA = 401;
    private static final int COLOR_BG = 0xFFF4F7FB;
    private static final int COLOR_INK = 0xFF10233C;
    private static final int COLOR_MUTED = 0xFF6B7C8F;
    private static final int COLOR_BLUE = 0xFF1467E8;
    private static final int COLOR_GREEN = 0xFF067647;
    private static final int COLOR_RED = 0xFFB42318;
    private static final String[] STEP_NAMES = {"排版", "打印", "覆膜", "裁切", "综合"};
    private static final String[] PROCESS_NAMES = {
            "排版", "写真打印", "写真过板", "写真覆膜", "裁切", "写真亚克力加工",
            "特殊亚克力排版", "亚克力排版", "打印", "过胶", "UV雪弗板覆膜", "覆膜",
            "激光切割", "UV雪弗板裁切", "雪弗板切割", "特殊亚克力加工",
    };

    private SharedPreferences prefs;
    private SSLContext sslContext;
    private String serverIp = "";
    private JSONArray jobs = new JSONArray();
    private JSONArray skillCatalog = new JSONArray();
    private int titleTaps = 0;
    private long lastTapAt = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.WHITE);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        serverIp = prefs.getString(K_IP, "");
        if (!serverIp.isEmpty() && loadSsl()) {
            if (!prefs.getString(K_TOKEN, "").isEmpty()) {
                if (prefs.getBoolean(K_IS_ADMIN, false)) {
                    showAdminDashboard();
                } else {
                    showLoading("正在连接服务器…");
                    refreshBootstrap(true);
                }
            } else {
                showLogin("");
            }
        } else {
            showSetup("");
        }
    }

    // ---------- 基础 UI ----------

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }

    private LinearLayout root() {
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(dp(24), dp(28), dp(24), dp(24));
        layout.setBackgroundColor(COLOR_BG);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.addView(layout, new ScrollView.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        setContentView(scroll);
        return layout;
    }

    private TextView text(String value, float size, int color, boolean bold) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(color);
        view.setLineSpacing(dp(4), 1.15f);
        if (bold) view.setTypeface(Typeface.create("sans-serif", Typeface.BOLD));
        return view;
    }

    private void add(LinearLayout parent, View view, int top) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        params.topMargin = dp(top);
        parent.addView(view, params);
    }

    private EditText input(String hint, int inputType) {
        EditText edit = new EditText(this);
        edit.setHint(hint);
        edit.setHintTextColor(0xFF9AA8B6);
        edit.setTextColor(COLOR_INK);
        edit.setTextSize(20);
        edit.setSingleLine(true);
        edit.setInputType(inputType);
        edit.setPadding(dp(16), dp(14), dp(16), dp(14));
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.WHITE);
        bg.setCornerRadius(dp(12));
        bg.setStroke(dp(1), 0xFFDCE5EF);
        edit.setBackground(bg);
        return edit;
    }

    private Button button(String label, int color) {
        Button button = new Button(this);
        button.setText(label);
        button.setTextSize(19);
        button.setTextColor(Color.WHITE);
        button.setAllCaps(false);
        button.setTypeface(Typeface.create("sans-serif", Typeface.BOLD));
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(color);
        bg.setCornerRadius(dp(14));
        button.setBackground(bg);
        button.setPadding(dp(10), 0, dp(10), 0);
        return button;
    }

    private Button smallButton(String label) {
        Button button = button(label, 0xFFEAF2FF);
        button.setTextColor(COLOR_BLUE);
        button.setTextSize(15);
        return button;
    }

    private void toast(String message) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }

    private void dialog(String title, String message) {
        new AlertDialog.Builder(this)
                .setTitle(title)
                .setMessage(message)
                .setPositiveButton("知道了", null)
                .show();
    }

    private String errorText(Throwable error) {
        if (error instanceof ApiException) {
            return error.getMessage();
        }
        String message = error.getMessage();
        return (message == null || message.isEmpty()) ? "连接失败，请检查 Wi-Fi 和服务器" : message;
    }

    // ---------- 首次配置 ----------

    private void showSetup(String message) {
        titleTaps = 0;
        LinearLayout layout = root();
        add(layout, text("计件通", 34, COLOR_INK, true), 0);
        add(layout, text("员工扫码版", 15, COLOR_MUTED, false), 4);
        add(layout, text("首次设置：输入服务器 IP", 20, COLOR_INK, true), 34);
        add(layout, text("由交付人员填写一次，员工以后不用再设置。", 13, COLOR_MUTED, false), 6);

        EditText ip = input("例如 192.168.2.8", InputType.TYPE_CLASS_TEXT);
        ip.setText(serverIp);
        add(layout, ip, 18);

        TextView status = text(message == null ? "" : message, 13,
                message != null && !message.isEmpty() ? COLOR_RED : COLOR_MUTED, false);
        add(layout, status, 10);

        Button save = button("保存并连接", COLOR_BLUE);
        save.setEnabled(true);
        add(layout, save, 16);

        Button test = smallButton("测试服务器连接");
        add(layout, test, 10);

        save.setOnClickListener(v -> setupServer(ip, status, save, test));
        test.setOnClickListener(v -> setupServer(ip, status, save, test));
    }

    private void setupServer(EditText ipInput, TextView status, Button save, Button test) {
        String raw = ipInput.getText().toString().trim();
        raw = raw.replace("http://", "").replace("https://", "").replace("/", "");
        if (!raw.matches("\\d{1,3}(\\.\\d{1,3}){3}")) {
            status.setTextColor(COLOR_RED);
            status.setText("请输入正确的服务器 IP，例如 192.168.2.8");
            return;
        }
        final String ip = raw;
        save.setEnabled(false);
        test.setEnabled(false);
        status.setTextColor(COLOR_MUTED);
        status.setText("正在连接服务器…");

        new Thread(() -> {
            try {
                byte[] ca = downloadCa(ip);
                SSLContext context = buildSsl(ca);
                String oldIp = serverIp;
                serverIp = ip;
                sslContext = context;
                JSONObject health = request("GET", "/api/health", null, false);
                if (!health.optBoolean("ok")) throw new Exception("服务器返回异常");
                prefs.edit()
                        .putString(K_IP, ip)
                        .putString(K_CA, Base64.encodeToString(ca, Base64.NO_WRAP))
                        .remove(K_TOKEN)
                        .apply();
                runOnUiThread(() -> {
                    Toast.makeText(this, "服务器连接成功", Toast.LENGTH_SHORT).show();
                    showLogin("");
                });
            } catch (Exception error) {
                serverIp = prefs.getString(K_IP, "");
                runOnUiThread(() -> {
                    save.setEnabled(true);
                    test.setEnabled(true);
                    status.setTextColor(COLOR_RED);
                    status.setText("连接失败：" + errorText(error));
                });
            }
        }).start();
    }

    // ---------- 登录 ----------

    private void showLogin(String message) {
        LinearLayout layout = root();
        add(layout, text("登录计件通", 30, COLOR_INK, true), 0);
        add(layout, text("输入工号和 PIN，只需登录一次", 14, COLOR_MUTED, false), 6);

        EditText account = input("工号，例如 5", InputType.TYPE_CLASS_TEXT);
        account.setText(prefs.getString(K_NO, ""));
        add(layout, account, 26);

        EditText pin = input("PIN", InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        add(layout, pin, 12);

        TextView status = text(message == null ? "" : message, 13,
                message != null && !message.isEmpty() ? COLOR_RED : COLOR_MUTED, false);
        add(layout, status, 10);

        Button login = button("登录", COLOR_BLUE);
        add(layout, login, 16);

        login.setOnClickListener(v -> {
            String no = account.getText().toString().trim();
            String secret = pin.getText().toString().trim();
            if (no.isEmpty() || secret.isEmpty()) {
                status.setTextColor(COLOR_RED);
                status.setText("请输入工号和 PIN");
                return;
            }
            login.setEnabled(false);
            status.setTextColor(COLOR_MUTED);
            status.setText("正在登录…");
            new Thread(() -> {
                try {
                    JSONObject body = new JSONObject();
                    body.put("account", no);
                    body.put("pin", secret);
                    JSONObject result = request("POST", "/api/login", body, false);
                    String token = result.getString("token");
                    JSONObject user = result.getJSONObject("user");
                    JSONArray jobList = result.optJSONArray("jobs");
                    boolean isAdmin = user.optBoolean("isAdmin", false);
                    prefs.edit()
                            .putString(K_TOKEN, token)
                            .putString(K_NAME, user.optString("name", ""))
                            .putString(K_NO, no)
                            .putString(K_ID, user.optString("id", ""))
                            .putBoolean(K_IS_ADMIN, isAdmin)
                            .putString(K_JOBS, jobList == null ? "[]" : jobList.toString())
                            .apply();
                    jobs = jobList == null ? new JSONArray() : jobList;
                    runOnUiThread(() -> {
                        if (isAdmin) showAdminDashboard();
                        else showHome();
                    });
                } catch (Exception error) {
                    runOnUiThread(() -> {
                        login.setEnabled(true);
                        status.setTextColor(COLOR_RED);
                        status.setText(errorText(error));
                    });
                }
            }).start();
        });

        Button change = smallButton("重新设置服务器");
        add(layout, change, 12);
        change.setOnClickListener(v -> showSetup(""));
    }

    // ---------- 首页 ----------

    private void showHome() {
        titleTaps = 0;
        LinearLayout layout = root();
        TextView title = text("计件通", 30, COLOR_INK, true);
        add(layout, title, 0);
        title.setOnClickListener(v -> {
            long now = System.currentTimeMillis();
            if (now - lastTapAt > 1200) titleTaps = 0;
            lastTapAt = now;
            titleTaps++;
            if (titleTaps >= 6) {
                titleTaps = 0;
                showSetup("");
            }
        });

        String name = prefs.getString(K_NAME, "");
        add(layout, text((name.isEmpty() ? "你好" : name + "，你好"), 23, COLOR_INK, true), 26);
        add(layout, text("对准流转卡二维码，系统自动报工", 14, COLOR_MUTED, false), 6);

        Button scan = button("扫 码 报 工", COLOR_BLUE);
        scan.setTextSize(27);
        int height = dp(150);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, height);
        params.topMargin = dp(28);
        layout.addView(scan, params);
        scan.setOnClickListener(v -> startScan());

        add(layout, text("不需要输入数量，扫到就自动提交", 13, COLOR_MUTED, false), 12);
        add(layout, text("服务器：" + serverIp, 11, 0xFF9AA8B6, false), 24);

        Button stats = smallButton("我的统计");
        add(layout, stats, 14);
        stats.setOnClickListener(v -> showStats());

        Button manual = smallButton("扫不出来？手动输入订单号");
        add(layout, manual, 14);
        manual.setOnClickListener(v -> {
            EditText code = input("输入订单号或流转码", InputType.TYPE_CLASS_TEXT);
            new AlertDialog.Builder(this)
                    .setTitle("手动报工")
                    .setMessage("输入流转卡上的订单号或 QJ 开头的流转码")
                    .setView(code)
                    .setNegativeButton("取消", null)
                    .setPositiveButton("查找并报工", (dialog, which) -> {
                        String value = code.getText().toString().trim();
                        if (value.isEmpty()) toast("请输入订单号");
                        else handleCode(value);
                    })
                    .show();
        });

        Button switchUser = smallButton("切换工号");
        add(layout, switchUser, 12);
        switchUser.setOnClickListener(v -> {
            prefs.edit().remove(K_TOKEN).remove(K_IS_ADMIN).apply();
            showLogin("");
        });

        Button settings = smallButton("服务器设置");
        add(layout, settings, 8);
        settings.setOnClickListener(v -> showSetup(""));
    }

    // ---------- 我的统计 ----------

    private void showStats() {
        showLoading("正在加载统计…");
        new Thread(() -> {
            try {
                JSONObject result = request("GET", "/api/bootstrap", null, true);
                JSONArray jobList = result.optJSONArray("jobs");
                JSONArray recordList = result.optJSONArray("records");
                JSONObject user = result.optJSONObject("user");
                if (jobList != null) {
                    jobs = jobList;
                    prefs.edit().putString(K_JOBS, jobList.toString()).apply();
                }
                if (user != null) {
                    prefs.edit()
                            .putString(K_NAME, user.optString("name", ""))
                            .putString(K_ID, user.optString("id", prefs.getString(K_ID, "")))
                            .apply();
                }
                final JSONArray finalJobs = jobList == null ? jobs : jobList;
                final JSONArray finalRecords = recordList == null ? new JSONArray() : recordList;
                runOnUiThread(() -> renderStats(finalRecords, finalJobs));
            } catch (ApiException error) {
                if (error.status == 401) {
                    prefs.edit().remove(K_TOKEN).apply();
                    runOnUiThread(() -> showLogin("登录已过期，请重新登录"));
                } else {
                    runOnUiThread(() -> {
                        showHome();
                        dialog("统计加载失败", error.getMessage());
                    });
                }
            } catch (Exception error) {
                runOnUiThread(() -> {
                    showHome();
                    dialog("统计加载失败", errorText(error));
                });
            }
        }).start();
    }

    private void renderStats(JSONArray records, JSONArray jobList) {
        String employeeId = prefs.getString(K_ID, "");
        String employeeName = prefs.getString(K_NAME, "");
        String employeeNo = prefs.getString(K_NO, "");

        Map<String, String> orderNos = new HashMap<>();
        for (int i = 0; i < jobList.length(); i++) {
            JSONObject job = jobList.optJSONObject(i);
            if (job != null) orderNos.put(job.optString("id"), job.optString("orderNo"));
        }

        SimpleDateFormat dayFormat = new SimpleDateFormat("yyyy-MM-dd", Locale.CHINA);
        SimpleDateFormat timeFormat = new SimpleDateFormat("MM-dd HH:mm", Locale.CHINA);
        String today = dayFormat.format(new Date());
        String month = today.substring(0, 7);
        Map<String, Double> todayTotals = new LinkedHashMap<>();
        Map<String, Double> monthTotals = new LinkedHashMap<>();
        List<JSONObject> recent = new ArrayList<>();
        int pending = 0;
        int todayCount = 0;

        for (int i = 0; i < records.length(); i++) {
            JSONObject record = records.optJSONObject(i);
            if (record == null) continue;
            if (!employeeId.equals(record.optString("employeeId"))) continue;
            String status = record.optString("status");
            if ("pending".equals(status)) {
                pending++;
                continue;
            }
            if (!"valid".equals(status)) continue;

            Date at = parseIso(record.optString("at"));
            String day = at == null ? "" : dayFormat.format(at);
            String unit = record.optString("unit", "");
            double qty = record.optDouble("qty", 0);
            if (day.equals(today)) {
                addTotal(todayTotals, unit, qty);
                todayCount++;
            }
            if (day.startsWith(month)) {
                addTotal(monthTotals, unit, qty);
            }
            if (recent.size() < 10) recent.add(record);
        }

        LinearLayout layout = root();
        add(layout, text("我的统计", 30, COLOR_INK, true), 0);
        String who = employeeName.isEmpty() ? "员工" : employeeName;
        if (!employeeNo.isEmpty()) who += " · 工号 " + employeeNo;
        add(layout, text(who, 14, COLOR_MUTED, false), 6);

        add(layout, text("今日报工 " + todayCount + " 笔", 16, COLOR_INK, true), 22);
        if (todayTotals.isEmpty()) {
            add(layout, text("今天还没有报工", 14, COLOR_MUTED, false), 6);
        } else {
            for (Map.Entry<String, Double> entry : todayTotals.entrySet()) {
                add(layout, text(entry.getKey() + "  " + formatQty(entry.getValue()), 20, COLOR_BLUE, true), 4);
            }
        }

        add(layout, text("本月合计", 16, COLOR_INK, true), 22);
        if (monthTotals.isEmpty()) {
            add(layout, text("本月还没有报工", 14, COLOR_MUTED, false), 6);
        } else {
            for (Map.Entry<String, Double> entry : monthTotals.entrySet()) {
                add(layout, text(entry.getKey() + "  " + formatQty(entry.getValue()), 20, COLOR_INK, true), 4);
            }
        }

        if (pending > 0) {
            add(layout, text("待厂长确认 " + pending + " 笔", 14, COLOR_RED, true), 14);
        }

        add(layout, text("最近报工", 17, COLOR_INK, true), 24);
        if (recent.isEmpty()) {
            add(layout, text("还没有报工记录", 14, COLOR_MUTED, false), 6);
        } else {
            for (JSONObject record : recent) {
                String jobId = record.optString("jobId");
                String orderNo = orderNos.get(jobId);
                if (orderNo == null || orderNo.isEmpty()) orderNo = jobId;
                int step = record.optInt("stepNo", 1);
                String stepName = (step >= 1 && step <= STEP_NAMES.length)
                        ? STEP_NAMES[step - 1] : ("第" + step + "道");
                String time = "";
                Date at = parseIso(record.optString("at"));
                if (at != null) time = timeFormat.format(at);
                String line = time + "  " + orderNo + "\n"
                        + stepName + "  " + formatQty(record.optDouble("qty", 0))
                        + " " + record.optString("unit", "");
                TextView row = text(line, 14, COLOR_INK, false);
                row.setPadding(0, dp(8), 0, dp(8));
                add(layout, row, 2);
                View divider = new View(this);
                divider.setBackgroundColor(0xFFE3EAF2);
                add(layout, divider, 2);
                divider.getLayoutParams().height = dp(1);
            }
        }

        Button back = button("返回首页", COLOR_BLUE);
        add(layout, back, 24);
        back.setOnClickListener(v -> showHome());
    }

    private void addTotal(Map<String, Double> totals, String unit, double qty) {
        String key = (unit == null || unit.isEmpty()) ? "未计单位" : unit;
        Double old = totals.get(key);
        totals.put(key, (old == null ? 0 : old) + qty);
    }

    private Date parseIso(String value) {
        if (value == null || value.length() < 19) return null;
        try {
            SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US);
            format.setTimeZone(TimeZone.getTimeZone("UTC"));
            return format.parse(value.substring(0, 19));
        } catch (Exception error) {
            return null;
        }
    }

    private String formatQty(double qty) {
        return new DecimalFormat("0.##").format(qty);
    }

    private void showAfterAuth() {
        if (prefs.getBoolean(K_IS_ADMIN, false)) {
            showAdminDashboard();
        } else {
            showHome();
        }
    }

    // ---------- 厂长手机统计 ----------

    private void showAdminDashboard() {
        showLoading("正在加载厂长统计…");
        new Thread(() -> {
            try {
                JSONObject result = request("GET", "/api/bootstrap", null, true);
                JSONArray jobList = result.optJSONArray("jobs");
                JSONArray recordList = result.optJSONArray("records");
                JSONArray employeeList = result.optJSONArray("employees");
                JSONObject user = result.optJSONObject("user");
                if (jobList != null) {
                    jobs = jobList;
                    prefs.edit().putString(K_JOBS, jobList.toString()).apply();
                }
                if (user != null) {
                    prefs.edit()
                            .putString(K_NAME, user.optString("name", ""))
                            .putString(K_ID, user.optString("id", ""))
                            .putBoolean(K_IS_ADMIN, user.optBoolean("isAdmin", false))
                            .apply();
                }
                final JSONArray finalRecords = recordList == null ? new JSONArray() : recordList;
                final JSONArray finalJobs = jobList == null ? jobs : jobList;
                final JSONArray finalEmployees = employeeList == null ? new JSONArray() : employeeList;
                runOnUiThread(() -> renderAdminDashboard(finalRecords, finalJobs, finalEmployees));
            } catch (ApiException error) {
                if (error.status == 401) {
                    prefs.edit().remove(K_TOKEN).remove(K_IS_ADMIN).apply();
                    runOnUiThread(() -> showLogin("登录已过期，请重新登录"));
                } else {
                    runOnUiThread(() -> {
                        showLogin("无法连接服务器：" + error.getMessage());
                    });
                }
            } catch (Exception error) {
                runOnUiThread(() -> showLogin("无法连接服务器：" + errorText(error)));
            }
        }).start();
    }

    private void renderAdminDashboard(JSONArray records, JSONArray jobList, JSONArray employeeList) {
        String adminName = prefs.getString(K_NAME, "厂长");
        Map<String, String> employeeNames = new HashMap<>();
        Map<String, Boolean> employeeAdmin = new HashMap<>();
        for (int i = 0; i < employeeList.length(); i++) {
            JSONObject employee = employeeList.optJSONObject(i);
            if (employee == null) continue;
            String id = employee.optString("id");
            employeeNames.put(id, employee.optString("name", id));
            employeeAdmin.put(id, employee.optBoolean("isAdmin", false));
        }

        Map<String, String> orderNos = new HashMap<>();
        int activeJobs = 0;
        for (int i = 0; i < jobList.length(); i++) {
            JSONObject job = jobList.optJSONObject(i);
            if (job == null) continue;
            orderNos.put(job.optString("id"), job.optString("orderNo"));
            if ("active".equals(job.optString("status"))) activeJobs++;
        }

        SimpleDateFormat dayFormat = new SimpleDateFormat("yyyy-MM-dd", Locale.CHINA);
        SimpleDateFormat timeFormat = new SimpleDateFormat("MM-dd HH:mm", Locale.CHINA);
        SimpleDateFormat dateLabel = new SimpleDateFormat("MM月dd日", Locale.CHINA);
        String today = dayFormat.format(new Date());
        String month = today.substring(0, 7);
        Map<String, Double> todayTotals = new LinkedHashMap<>();
        Map<String, Double> monthTotals = new LinkedHashMap<>();
        Map<String, Map<String, Double>> employeeTotals = new LinkedHashMap<>();
        Map<String, Map<String, Double>> stepTotals = new LinkedHashMap<>();
        List<JSONObject> recent = new ArrayList<>();
        int pending = 0;
        int todayCount = 0;

        for (int i = 0; i < records.length(); i++) {
            JSONObject record = records.optJSONObject(i);
            if (record == null) continue;
            String status = record.optString("status");
            if ("pending".equals(status)) {
                pending++;
                continue;
            }
            if (!"valid".equals(status)) continue;

            String employeeId = record.optString("employeeId");
            if (employeeAdmin.getOrDefault(employeeId, false)) continue;
            String unit = record.optString("unit", "");
            double qty = record.optDouble("qty", 0);
            Date at = parseIso(record.optString("at"));
            String day = at == null ? "" : dayFormat.format(at);
            if (day.equals(today)) {
                addTotal(todayTotals, unit, qty);
                todayCount++;
            }
            if (day.startsWith(month)) {
                addTotal(monthTotals, unit, qty);
                Map<String, Double> employeeMap = employeeTotals.get(employeeId);
                if (employeeMap == null) {
                    employeeMap = new LinkedHashMap<>();
                    employeeTotals.put(employeeId, employeeMap);
                }
                addTotal(employeeMap, unit, qty);
                String stepKey = String.valueOf(record.optInt("stepNo", 1));
                Map<String, Double> stepMap = stepTotals.get(stepKey);
                if (stepMap == null) {
                    stepMap = new LinkedHashMap<>();
                    stepTotals.put(stepKey, stepMap);
                }
                addTotal(stepMap, unit, qty);
            }
            if (recent.size() < 8) recent.add(record);
        }

        LinearLayout layout = root();
        add(layout, text("厂长统计", 30, COLOR_INK, true), 0);
        add(layout, text(adminName + " · 厂长手机版", 14, COLOR_MUTED, false), 6);

        add(layout, text("今日 " + dateLabel.format(new Date()) + " · " + todayCount + " 笔", 16, COLOR_INK, true), 22);
        if (todayTotals.isEmpty()) {
            add(layout, text("今天还没有报工", 14, COLOR_MUTED, false), 6);
        } else {
            for (Map.Entry<String, Double> entry : todayTotals.entrySet()) {
                add(layout, text(entry.getKey() + "  " + formatQty(entry.getValue()), 22, COLOR_BLUE, true), 4);
            }
        }

        add(layout, text("本月合计", 16, COLOR_INK, true), 22);
        if (monthTotals.isEmpty()) {
            add(layout, text("本月还没有报工", 14, COLOR_MUTED, false), 6);
        } else {
            for (Map.Entry<String, Double> entry : monthTotals.entrySet()) {
                add(layout, text(entry.getKey() + "  " + formatQty(entry.getValue()), 22, COLOR_INK, true), 4);
            }
        }

        LinearLayout summary = new LinearLayout(this);
        summary.setOrientation(LinearLayout.HORIZONTAL);
        summary.setPadding(dp(14), dp(12), dp(14), dp(12));
        GradientDrawable summaryBg = new GradientDrawable();
        summaryBg.setColor(Color.WHITE);
        summaryBg.setCornerRadius(dp(12));
        summary.setBackground(summaryBg);
        TextView pendingView = text("待确认 " + pending + " 笔", 14, pending > 0 ? COLOR_RED : COLOR_MUTED, true);
        TextView jobsView = text("进行中订单 " + activeJobs + " 个", 14, COLOR_MUTED, true);
        summary.addView(pendingView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        summary.addView(jobsView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        add(layout, summary, 16);

        add(layout, text("员工产量（本月）", 17, COLOR_INK, true), 24);
        boolean anyEmployee = false;
        for (int i = 0; i < employeeList.length(); i++) {
            JSONObject employee = employeeList.optJSONObject(i);
            if (employee == null) continue;
            String id = employee.optString("id");
            if (employeeAdmin.getOrDefault(id, false)) continue;
            Map<String, Double> totals = employeeTotals.get(id);
            if (totals == null || totals.isEmpty()) continue;
            anyEmployee = true;
            add(layout, text(employee.optString("name", id) + "  " + formatUnits(totals), 15, COLOR_INK, true), 8);
        }
        if (!anyEmployee) add(layout, text("本月还没有员工报工", 14, COLOR_MUTED, false), 6);

        add(layout, text("工序产出（本月）", 17, COLOR_INK, true), 24);
        if (stepTotals.isEmpty()) {
            add(layout, text("本月还没有工序数据", 14, COLOR_MUTED, false), 6);
        } else {
            for (int step = 1; step <= STEP_NAMES.length; step++) {
                Map<String, Double> totals = stepTotals.get(String.valueOf(step));
                if (totals == null || totals.isEmpty()) continue;
                add(layout, text(STEP_NAMES[step - 1] + "  " + formatUnits(totals), 15, COLOR_INK, true), 6);
            }
        }

        add(layout, text("最近报工", 17, COLOR_INK, true), 24);
        if (recent.isEmpty()) {
            add(layout, text("还没有报工记录", 14, COLOR_MUTED, false), 6);
        } else {
            for (JSONObject record : recent) {
                String employee = employeeNames.getOrDefault(record.optString("employeeId"), record.optString("employeeId"));
                String orderNo = orderNos.getOrDefault(record.optString("jobId"), record.optString("jobId"));
                int step = record.optInt("stepNo", 1);
                String stepName = (step >= 1 && step <= STEP_NAMES.length) ? STEP_NAMES[step - 1] : ("第" + step + "道");
                Date at = parseIso(record.optString("at"));
                String time = at == null ? "" : timeFormat.format(at);
                String line = time + "  " + employee + "\n" + orderNo + " · " + stepName + "  "
                        + formatQty(record.optDouble("qty", 0)) + " " + record.optString("unit", "");
                add(layout, text(line, 13, COLOR_INK, false), 8);
            }
        }

        Button orders = button("订单管理", COLOR_BLUE);
        add(layout, orders, 24);
        orders.setOnClickListener(v -> showOrderManager());

        Button employees = button("员工管理", COLOR_BLUE);
        add(layout, employees, 8);
        employees.setOnClickListener(v -> showEmployeeManager());

        Button clear = smallButton("清空生产数据");
        add(layout, clear, 8);
        clear.setOnClickListener(v -> showClearDataDialog());

        Button refresh = button("刷新统计", COLOR_BLUE);
        add(layout, refresh, 10);
        refresh.setOnClickListener(v -> showAdminDashboard());

        Button switchUser = smallButton("切换账号");
        add(layout, switchUser, 10);
        switchUser.setOnClickListener(v -> {
            prefs.edit().remove(K_TOKEN).remove(K_IS_ADMIN).apply();
            showLogin("");
        });

        Button settings = smallButton("服务器设置");
        add(layout, settings, 8);
        settings.setOnClickListener(v -> showSetup(""));
    }

    private void showOrderManager() {
        showLoading("正在加载订单…");
        new Thread(() -> {
            try {
                JSONObject result = request("GET", "/api/bootstrap", null, true);
                JSONArray jobList = result.optJSONArray("jobs");
                JSONArray recordList = result.optJSONArray("records");
                JSONArray employeeList = result.optJSONArray("employees");
                if (jobList != null) {
                    jobs = jobList;
                    prefs.edit().putString(K_JOBS, jobList.toString()).apply();
                }
                final JSONArray finalJobs = jobList == null ? jobs : jobList;
                final JSONArray finalRecords = recordList == null ? new JSONArray() : recordList;
                final JSONArray finalEmployees = employeeList == null ? new JSONArray() : employeeList;
                runOnUiThread(() -> renderOrderManager(finalJobs, finalRecords, finalEmployees));
            } catch (ApiException error) {
                if (error.status == 401) {
                    prefs.edit().remove(K_TOKEN).remove(K_IS_ADMIN).apply();
                    runOnUiThread(() -> showLogin("登录已过期，请重新登录"));
                } else {
                    runOnUiThread(() -> dialog("订单加载失败", error.getMessage()));
                }
            } catch (Exception error) {
                runOnUiThread(() -> dialog("订单加载失败", errorText(error)));
            }
        }).start();
    }

    private void renderOrderManager(JSONArray jobList, JSONArray recordList, JSONArray employeeList) {
        LinearLayout layout = root();
        add(layout, text("订单管理", 30, COLOR_INK, true), 0);
        add(layout, text("修改订单号、米数、备注；已报工订单不能改米数", 13, COLOR_MUTED, false), 6);

        int shown = 0;
        for (int i = 0; i < jobList.length(); i++) {
            JSONObject job = jobList.optJSONObject(i);
            if (job == null || !"active".equals(job.optString("status"))) continue;
            shown++;
            String orderNo = job.optString("orderNo", job.optString("id"));
            String line = job.optString("line", "");
            String unit = job.optString("unit", "");
            double meters = job.optDouble("meters", 0);
            String remark = job.optString("remark", "");
            add(layout, text(orderNo, 17, COLOR_INK, true), 18);
            String sub = line + " · " + formatQty(meters) + " " + unit;
            if (!remark.isEmpty()) sub += " · " + remark;
            add(layout, text(sub, 13, COLOR_MUTED, false), 4);

            StringBuilder stepsLine = new StringBuilder();
            JSONArray jobSteps = job.optJSONArray("steps");
            if (jobSteps != null) {
                for (int s = 0; s < jobSteps.length(); s++) {
                    JSONObject step = jobSteps.optJSONObject(s);
                    if (step == null) continue;
                    int no = step.optInt("no");
                    String name = step.optString("name", "第" + no + "道");
                    boolean done = false;
                    boolean pending = false;
                    for (int r = 0; r < recordList.length(); r++) {
                        JSONObject rec = recordList.optJSONObject(r);
                        if (rec == null || !job.optString("id").equals(rec.optString("jobId"))) continue;
                        if (rec.optInt("stepNo") != no) continue;
                        if ("valid".equals(rec.optString("status"))) done = true;
                        if ("pending".equals(rec.optString("status"))) pending = true;
                    }
                    JSONObject group = step.optJSONObject("group");
                    String mark = done ? "✓" : (pending ? "!" : "○");
                    if (group != null && "open".equals(group.optString("status"))) {
                        mark = "合报中 " + group.optInt("memberCount", 0) + "人";
                    }
                    if (stepsLine.length() > 0) stepsLine.append("  →  ");
                    stepsLine.append(mark).append(" ").append(name);
                }
            }
            add(layout, text(stepsLine.toString(), 12, COLOR_INK, false), 4);

            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            Button edit = smallButton("修改");
            Button voidJob = smallButton("作废");
            voidJob.setTextColor(COLOR_RED);
            LinearLayout.LayoutParams left = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
            left.rightMargin = dp(6);
            LinearLayout.LayoutParams right = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
            row.addView(edit, left);
            row.addView(voidJob, right);
            add(layout, row, 8);
            edit.setOnClickListener(v -> showEditJobDialog(job));
            voidJob.setOnClickListener(v -> confirmVoidJob(job));
            Button complete = smallButton("完成订单");
            add(layout, complete, 6);
            complete.setOnClickListener(v -> confirmCompleteJob(job));
            View divider = new View(this);
            divider.setBackgroundColor(0xFFE3EAF2);
            add(layout, divider, 8);
            divider.getLayoutParams().height = dp(1);
        }
        if (shown == 0) add(layout, text("没有进行中的订单", 14, COLOR_MUTED, false), 16);

        Button back = button("返回厂长统计", COLOR_BLUE);
        add(layout, back, 24);
        back.setOnClickListener(v -> showAdminDashboard());
    }

    private void showEditJobDialog(JSONObject job) {
        LinearLayout form = new LinearLayout(this);
        form.setOrientation(LinearLayout.VERTICAL);
        form.setPadding(dp(20), dp(8), dp(20), 0);
        EditText orderNo = input("订单号", InputType.TYPE_CLASS_TEXT);
        orderNo.setText(job.optString("orderNo", ""));
        EditText meters = input("米数/数量", InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
        meters.setText(formatQty(job.optDouble("meters", 0)));
        EditText remark = input("备注", InputType.TYPE_CLASS_TEXT);
        remark.setText(job.optString("remark", ""));
        form.addView(orderNo);
        form.addView(meters);
        form.addView(remark);
        new AlertDialog.Builder(this)
                .setTitle("修改订单")
                .setMessage("已报工的订单只能改订单号或备注，不能改米数。")
                .setView(form)
                .setNegativeButton("取消", null)
                .setPositiveButton("保存", (dialog, which) -> {
                    try {
                        String no = orderNo.getText().toString().trim();
                        if (no.isEmpty()) {
                            toast("订单号不能为空");
                            return;
                        }
                        double qty = Double.parseDouble(meters.getText().toString().trim());
                        JSONObject body = new JSONObject();
                        body.put("orderNo", no);
                        body.put("meters", qty);
                        body.put("remark", remark.getText().toString().trim());
                        submitJobEdit(job.optString("id"), body);
                    } catch (Exception error) {
                        toast("米数格式不正确");
                    }
                })
                .show();
    }

    private void submitJobEdit(String jobId, JSONObject body) {
        showLoading("正在保存订单…");
        new Thread(() -> {
            try {
                request("PATCH", "/api/admin/jobs/" + jobId, body, true);
                runOnUiThread(() -> {
                    toast("订单已修改");
                    showOrderManager();
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    showOrderManager();
                    dialog("修改失败", errorText(error));
                });
            }
        }).start();
    }

    private void confirmVoidJob(JSONObject job) {
        String orderNo = job.optString("orderNo", job.optString("id"));
        new AlertDialog.Builder(this)
                .setTitle("作废订单")
                .setMessage("确定作废 " + orderNo + " 吗？\n\n作废后不能再报工，相关报工记录会标记为作废，但会保留审计记录。")
                .setNegativeButton("取消", null)
                .setPositiveButton("确认作废", (dialog, which) -> submitVoidJob(job.optString("id")))
                .show();
    }

    private void submitVoidJob(String jobId) {
        showLoading("正在作废订单…");
        new Thread(() -> {
            try {
                JSONObject body = new JSONObject();
                body.put("reason", "厂长手机作废");
                request("POST", "/api/admin/jobs/" + jobId + "/void", body, true);
                runOnUiThread(() -> {
                    toast("订单已作废");
                    showOrderManager();
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    showOrderManager();
                    dialog("作废失败", errorText(error));
                });
            }
        }).start();
    }

    private void confirmCompleteJob(JSONObject job) {
        String orderNo = job.optString("orderNo", job.optString("id"));
        new AlertDialog.Builder(this)
                .setTitle("完成订单")
                .setMessage("确认完成 " + orderNo + "？\n\n系统会先结束未关闭的合报组，再检查所有工序是否完成。")
                .setNegativeButton("取消", null)
                .setPositiveButton("确认完成", (dialog, which) -> submitCompleteJob(job.optString("id")))
                .show();
    }

    private void submitCompleteJob(String jobId) {
        showLoading("正在完成订单…");
        new Thread(() -> {
            try {
                request("POST", "/api/admin/jobs/" + jobId + "/complete", new JSONObject(), true);
                runOnUiThread(() -> {
                    toast("订单已完成");
                    showOrderManager();
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    showOrderManager();
                    dialog("完成失败", errorText(error));
                });
            }
        }).start();
    }

    private void showClearDataDialog() {
        LinearLayout form = new LinearLayout(this);
        form.setOrientation(LinearLayout.VERTICAL);
        form.setPadding(dp(20), dp(8), dp(20), 0);
        TextView warning = text("此操作会清空所有订单、报工和审批数据，但保留员工、技能和密码。清空前会自动备份数据库。", 13, COLOR_RED, false);
        EditText password = input("管理员密码", InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        EditText confirm = input("输入：清空", InputType.TYPE_CLASS_TEXT);
        form.addView(warning);
        form.addView(password);
        form.addView(confirm);
        new AlertDialog.Builder(this)
                .setTitle("清空生产数据")
                .setView(form)
                .setNegativeButton("取消", null)
                .setPositiveButton("确认清空", (dialog, which) -> submitClearData(
                        password.getText().toString().trim(),
                        confirm.getText().toString().trim()))
                .show();
    }

    private void submitClearData(String password, String confirm) {
        if (password.isEmpty()) {
            toast("请输入管理员密码");
            return;
        }
        if (!"清空".equals(confirm)) {
            toast("确认文字不对，请输入：清空");
            return;
        }
        showLoading("正在清空生产数据…");
        new Thread(() -> {
            try {
                JSONObject body = new JSONObject();
                body.put("password", password);
                body.put("confirm", confirm);
                request("POST", "/api/admin/clear-data", body, true);
                runOnUiThread(() -> {
                    toast("生产数据已清空，数据库已备份");
                    showAdminDashboard();
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    showAdminDashboard();
                    dialog("清空失败", errorText(error));
                });
            }
        }).start();
    }

    private void showEmployeeManager() {
        showLoading("正在加载员工…");
        new Thread(() -> {
            try {
                JSONObject result = request("GET", "/api/bootstrap", null, true);
                JSONArray employeeList = result.optJSONArray("employees");
                JSONArray skills = result.optJSONArray("skills");
                if (skills != null) skillCatalog = skills;
                final JSONArray finalEmployees = employeeList == null ? new JSONArray() : employeeList;
                runOnUiThread(() -> renderEmployeeManager(finalEmployees));
            } catch (Exception error) {
                runOnUiThread(() -> dialog("员工加载失败", errorText(error)));
            }
        }).start();
    }

    private void renderEmployeeManager(JSONArray employeeList) {
        LinearLayout layout = root();
        add(layout, text("员工管理", 30, COLOR_INK, true), 0);
        add(layout, text("添加员工、修改姓名/岗位、修改工序技能", 13, COLOR_MUTED, false), 6);

        Button addEmployee = button("+ 添加员工", COLOR_BLUE);
        add(layout, addEmployee, 16);
        addEmployee.setOnClickListener(v -> showAddEmployeeDialog());

        for (int i = 0; i < employeeList.length(); i++) {
            JSONObject employee = employeeList.optJSONObject(i);
            if (employee == null || employee.optBoolean("isAdmin", false)) continue;
            String name = employee.optString("name", employee.optString("id"));
            String role = employee.optString("role", "");
            add(layout, text(name + " · " + role + " · 工号 " + employee.optInt("employeeNo"), 16, COLOR_INK, true), 16);
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            Button rename = smallButton("改名/岗位");
            Button skills = smallButton("改技能");
            LinearLayout.LayoutParams a = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
            a.rightMargin = dp(6);
            LinearLayout.LayoutParams b = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
            row.addView(rename, a);
            row.addView(skills, b);
            add(layout, row, 6);
            rename.setOnClickListener(v -> showEditEmployeeDialog(employee));
            skills.setOnClickListener(v -> showEmployeeSkillsDialog(employee));
        }

        Button back = button("返回厂长统计", COLOR_BLUE);
        add(layout, back, 24);
        back.setOnClickListener(v -> showAdminDashboard());
    }

    private void showAddEmployeeDialog() {
        LinearLayout form = new LinearLayout(this);
        form.setOrientation(LinearLayout.VERTICAL);
        form.setPadding(dp(20), dp(8), dp(20), 0);
        EditText name = input("姓名", InputType.TYPE_CLASS_TEXT);
        EditText no = input("工号，例如 18", InputType.TYPE_CLASS_NUMBER);
        EditText pin = input("初始 PIN（6 位）", InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        EditText role = input("岗位，例如 综合岗位", InputType.TYPE_CLASS_TEXT);
        form.addView(name); form.addView(no); form.addView(pin); form.addView(role);
        new AlertDialog.Builder(this)
                .setTitle("添加员工")
                .setMessage("创建后可在“改技能”里设置工序；员工立即可以登录。")
                .setView(form)
                .setNegativeButton("取消", null)
                .setPositiveButton("创建", (dialog, which) -> submitAddEmployee(
                        name.getText().toString().trim(),
                        no.getText().toString().trim(),
                        pin.getText().toString().trim(),
                        role.getText().toString().trim()))
                .show();
    }

    private void submitAddEmployee(String name, String noText, String pin, String role) {
        int no;
        try {
            no = Integer.parseInt(noText);
        } catch (Exception error) {
            toast("工号必须是数字");
            return;
        }
        showLoading("正在创建员工…");
        new Thread(() -> {
            try {
                JSONObject body = new JSONObject();
                body.put("name", name);
                body.put("employeeNo", no);
                body.put("pin", pin);
                body.put("role", role.isEmpty() ? "员工" : role);
                body.put("canCreateJob", false);
                body.put("processSkills", new JSONArray());
                request("POST", "/api/admin/employees", body, true);
                runOnUiThread(() -> {
                    toast("员工已添加");
                    showEmployeeManager();
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    showEmployeeManager();
                    dialog("添加失败", errorText(error));
                });
            }
        }).start();
    }

    private void showEditEmployeeDialog(JSONObject employee) {
        LinearLayout form = new LinearLayout(this);
        form.setOrientation(LinearLayout.VERTICAL);
        form.setPadding(dp(20), dp(8), dp(20), 0);
        EditText name = input("姓名", InputType.TYPE_CLASS_TEXT);
        name.setText(employee.optString("name", ""));
        EditText role = input("岗位", InputType.TYPE_CLASS_TEXT);
        role.setText(employee.optString("role", ""));
        form.addView(name); form.addView(role);
        new AlertDialog.Builder(this)
                .setTitle("修改员工姓名/岗位")
                .setView(form)
                .setNegativeButton("取消", null)
                .setPositiveButton("保存", (dialog, which) -> submitEmployeeName(
                        employee.optString("id"),
                        name.getText().toString().trim(),
                        role.getText().toString().trim()))
                .show();
    }

    private void submitEmployeeName(String employeeId, String name, String role) {
        showLoading("正在保存…");
        new Thread(() -> {
            try {
                JSONObject body = new JSONObject();
                body.put("name", name);
                body.put("role", role);
                request("PATCH", "/api/admin/employees/" + employeeId, body, true);
                runOnUiThread(() -> {
                    toast("员工信息已修改");
                    showEmployeeManager();
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    showEmployeeManager();
                    dialog("修改失败", errorText(error));
                });
            }
        }).start();
    }

    private void showEmployeeSkillsDialog(JSONObject employee) {
        java.util.Set<String> selected = new java.util.HashSet<>();
        JSONArray current = employee.optJSONArray("processSkills");
        if (current != null) {
            for (int i = 0; i < current.length(); i++) selected.add(current.optString(i));
        }
        LinearLayout form = new LinearLayout(this);
        form.setOrientation(LinearLayout.VERTICAL);
        form.setPadding(dp(20), dp(8), dp(20), 0);
        boolean dynamic = skillCatalog.length() > 0;
        String[] names = new String[dynamic ? skillCatalog.length() : PROCESS_NAMES.length];
        String[] labels = new String[names.length];
        for (int i = 0; i < names.length; i++) {
            if (dynamic) {
                JSONObject skill = skillCatalog.optJSONObject(i);
                names[i] = skill == null ? "" : skill.optString("name");
                labels[i] = skill == null ? names[i] : skill.optString("displayName", names[i]);
            } else {
                names[i] = PROCESS_NAMES[i];
                labels[i] = PROCESS_NAMES[i];
            }
        }
        CheckBox[] boxes = new CheckBox[names.length];
        for (int i = 0; i < names.length; i++) {
            CheckBox box = new CheckBox(this);
            box.setText(labels[i]);
            box.setTextSize(14);
            box.setChecked(selected.contains(names[i]));
            boxes[i] = box;
            form.addView(box);
        }
        ScrollView scroll = new ScrollView(this);
        scroll.addView(form);
        new AlertDialog.Builder(this)
                .setTitle("修改工序技能")
                .setView(scroll)
                .setNegativeButton("取消", null)
                .setPositiveButton("保存", (dialog, which) -> {
                    JSONArray processes = new JSONArray();
                    for (int i = 0; i < boxes.length; i++) {
                        if (boxes[i].isChecked()) processes.put(names[i]);
                    }
                    submitEmployeeSkills(employee.optString("id"), processes);
                })
                .show();
    }

    private void submitEmployeeSkills(String employeeId, JSONArray processes) {
        showLoading("正在保存技能…");
        new Thread(() -> {
            try {
                JSONObject body = new JSONObject();
                body.put("processes", processes);
                request("PUT", "/api/admin/employees/" + employeeId + "/process-skills", body, true);
                runOnUiThread(() -> {
                    toast("工序技能已更新");
                    showEmployeeManager();
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    showEmployeeManager();
                    dialog("保存失败", errorText(error));
                });
            }
        }).start();
    }

    private String formatUnits(Map<String, Double> totals) {
        StringBuilder builder = new StringBuilder();
        for (Map.Entry<String, Double> entry : totals.entrySet()) {
            if (builder.length() > 0) builder.append("  ·  ");
            builder.append(entry.getKey()).append(" ").append(formatQty(entry.getValue()));
        }
        return builder.toString();
    }

    private void showLoading(String message) {
        LinearLayout layout = root();
        add(layout, text("计件通", 30, COLOR_INK, true), 0);
        add(layout, text(message, 16, COLOR_MUTED, false), 24);
    }

    // ---------- 扫码 ----------

    private void startScan() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.CAMERA}, REQ_CAMERA);
            return;
        }
        IntentIntegrator integrator = new IntentIntegrator(this);
        integrator.setDesiredBarcodeFormats(IntentIntegrator.QR_CODE);
        integrator.setPrompt("对准流转卡二维码");
        integrator.setBeepEnabled(false);
        integrator.setOrientationLocked(true);
        integrator.initiateScan();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions,
                                           @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQ_CAMERA) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                startScan();
            } else {
                dialog("需要相机权限", "请在手机设置中允许计件通使用相机，然后重试。");
            }
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        IntentResult result = IntentIntegrator.parseActivityResult(requestCode, resultCode, data);
        if (result != null) {
            if (result.getContents() != null) {
                handleCode(result.getContents());
            }
            return;
        }
        super.onActivityResult(requestCode, resultCode, data);
    }

    private void handleCode(String code) {
        if (code == null || code.trim().isEmpty()) return;
        JSONObject job = findJob(code.trim());
        if (job == null) {
            showLoading("正在查找订单…");
            new Thread(() -> {
                try {
                    refreshBootstrapSync();
                    JSONObject found = findJob(code.trim());
                    if (found == null) {
                        runOnUiThread(() -> {
                            showHome();
                            dialog("没有找到订单", "这张二维码不属于当前服务器，或订单不在最近数据中。");
                        });
                    } else {
                        autoReport(found);
                    }
                } catch (Exception error) {
                    runOnUiThread(() -> {
                        showHome();
                        dialog("查找订单失败", errorText(error));
                    });
                }
            }).start();
            return;
        }
        autoReport(job);
    }

    private JSONObject findJob(String code) {
        JSONArray list = jobs;
        String lower = code.toLowerCase();
        for (int i = 0; i < list.length(); i++) {
            JSONObject job = list.optJSONObject(i);
            if (job == null) continue;
            String qr = job.optString("qr", "");
            String no = job.optString("orderNo", "");
            String id = job.optString("id", "");
            if (lower.equals(qr.toLowerCase()) || lower.equals(no.toLowerCase())
                    || lower.equals(id.toLowerCase())
                    || lower.contains(no.toLowerCase())
                    || lower.contains(qr.toLowerCase())) {
                return job;
            }
        }
        return null;
    }

    private void autoReport(JSONObject job) {
        final String jobId = job.optString("id");
        final String orderNo = job.optString("orderNo");
        showLoading("正在检查可报岗位…");
        new Thread(() -> {
            try {
                JSONObject options = request("GET",
                        "/api/jobs/" + jobId + "/auto-report/options", null, true);
                JSONArray stepNos = options.optJSONArray("stepNos");
                if (stepNos == null || stepNos.length() == 0) {
                    runOnUiThread(() -> {
                        showHome();
                        dialog("没有可报岗位", "当前订单没有你可以报的工序，或该订单已经报完。");
                    });
                    return;
                }
                if (stepNos.length() == 1) {
                    submitAutoReport(jobId, orderNo, stepNos.optInt(0));
                    return;
                }
                final String[] names = new String[stepNos.length()];
                final int[] numbers = new int[stepNos.length()];
                for (int i = 0; i < stepNos.length(); i++) {
                    numbers[i] = stepNos.optInt(i);
                    names[i] = stepNameForLine(job.optString("line"), numbers[i]);
                }
                runOnUiThread(() -> new AlertDialog.Builder(this)
                        .setTitle("选择岗位")
                        .setMessage("你有多项技能，请选择这张订单你实际完成的工序")
                        .setItems(names, (dialog, which) ->
                                submitAutoReport(jobId, orderNo, numbers[which]))
                        .setNegativeButton("取消", null)
                        .show());
            } catch (Exception error) {
                runOnUiThread(() -> {
                    showHome();
                    dialog("报工失败", errorText(error));
                });
            }
        }).start();
    }

    private String stepNameForLine(String line, int stepNo) {
        if (stepNo >= 1 && stepNo <= STEP_NAMES.length) return STEP_NAMES[stepNo - 1];
        return "第" + stepNo + "道";
    }

    private void submitAutoReport(String jobId, String orderNo, int stepNo) {
        runOnUiThread(() -> showLoading("正在报工…"));
        new Thread(() -> {
            try {
                JSONObject body = new JSONObject();
                body.put("stepNo", stepNo);
                JSONObject result = request("POST", "/api/jobs/" + jobId + "/auto-report", body, true);
                JSONObject record = result.optJSONObject("record");
                JSONArray jobList = result.optJSONArray("jobs");
                if (jobList != null) {
                    jobs = jobList;
                    prefs.edit().putString(K_JOBS, jobList.toString()).apply();
                }
                if (record == null && result.optJSONObject("group") != null) {
                    JSONObject group = result.optJSONObject("group");
                    int count = group.optInt("memberCount", 1);
                    runOnUiThread(() -> {
                        showHome();
                        dialog("已加入合报", "当前共 " + count + " 人。\n下一道工序开始或厂长完成后，系统按实际人数平分。");
                    });
                    return;
                }
                if (record == null) throw new Exception("服务器没有返回报工记录");
                runOnUiThread(() -> showSuccess(record, orderNo));
            } catch (ApiException error) {
                if (error.status == 401) {
                    prefs.edit().remove(K_TOKEN).apply();
                    runOnUiThread(() -> showLogin("登录已过期，请重新登录"));
                } else {
                    runOnUiThread(() -> {
                        showHome();
                        dialog("报工失败", error.getMessage());
                    });
                }
            } catch (Exception error) {
                runOnUiThread(() -> {
                    showHome();
                    dialog("报工失败", errorText(error));
                });
            }
        }).start();
    }

    private void showSuccess(JSONObject record, String orderNo) {
        LinearLayout layout = root();
        add(layout, text("✓", 72, COLOR_GREEN, true), 20);
        add(layout, text("报工成功", 32, COLOR_GREEN, true), 0);
        add(layout, text("数量已计入你的今日产量", 15, COLOR_MUTED, false), 8);

        int step = record.optInt("stepNo", 1);
        String stepName = (step >= 1 && step <= STEP_NAMES.length) ? STEP_NAMES[step - 1] : ("第" + step + "道");
        String qty = record.optString("qty", "");
        String unit = record.optString("unit", "");

        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(18), dp(16), dp(18), dp(16));
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.WHITE);
        bg.setCornerRadius(dp(14));
        card.setBackground(bg);

        card.addView(text("订单号", 12, COLOR_MUTED, false));
        card.addView(text(orderNo, 22, COLOR_INK, true));
        card.addView(text("工序", 12, COLOR_MUTED, false));
        card.addView(text(stepName, 20, COLOR_INK, true));
        card.addView(text("本次数量", 12, COLOR_MUTED, false));
        card.addView(text(qty + " " + unit, 24, COLOR_BLUE, true));
        add(layout, card, 24);

        Button again = button("继续扫码报工", COLOR_BLUE);
        add(layout, again, 24);
        again.setOnClickListener(v -> startScan());

        Button home = smallButton("回到首页");
        add(layout, home, 10);
        home.setOnClickListener(v -> showHome());
    }

    // ---------- 网络 ----------

    private byte[] downloadCa(String ip) throws Exception {
        HttpURLConnection conn = (HttpURLConnection) new URL(
                "http://" + ip + ":8788/jitong-local-ca.cer").openConnection();
        conn.setConnectTimeout(8000);
        conn.setReadTimeout(8000);
        conn.setRequestMethod("GET");
        int code = conn.getResponseCode();
        if (code != 200) throw new Exception("无法下载手机证书（" + code + "）");
        InputStream input = conn.getInputStream();
        byte[] data = readAll(input);
        input.close();
        conn.disconnect();
        if (data.length < 100) throw new Exception("证书文件为空");
        return data;
    }

    private SSLContext buildSsl(byte[] ca) throws Exception {
        CertificateFactory factory = CertificateFactory.getInstance("X.509");
        Certificate certificate = factory.generateCertificate(new ByteArrayInputStream(ca));
        KeyStore keyStore = KeyStore.getInstance(KeyStore.getDefaultType());
        keyStore.load(null, null);
        keyStore.setCertificateEntry("jitong", certificate);
        TrustManagerFactory tmf = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
        tmf.init(keyStore);
        SSLContext context = SSLContext.getInstance("TLS");
        context.init(null, tmf.getTrustManagers(), null);
        return context;
    }

    private boolean loadSsl() {
        String encoded = prefs.getString(K_CA, "");
        if (encoded.isEmpty()) return false;
        try {
            byte[] ca = Base64.decode(encoded, Base64.DEFAULT);
            sslContext = buildSsl(ca);
            jobs = new JSONArray(prefs.getString(K_JOBS, "[]"));
            return true;
        } catch (Exception error) {
            return false;
        }
    }

    private void refreshBootstrap(boolean fromStart) {
        new Thread(() -> {
            try {
                refreshBootstrapSync();
                runOnUiThread(this::showAfterAuth);
            } catch (ApiException error) {
                if (error.status == 401) {
                    prefs.edit().remove(K_TOKEN).apply();
                    runOnUiThread(() -> showLogin(""));
                } else {
                    runOnUiThread(() -> {
                        if (fromStart) showLogin("无法连接服务器：" + error.getMessage());
                        else showHome();
                    });
                }
            } catch (Exception error) {
                runOnUiThread(() -> {
                    if (fromStart) showLogin("无法连接服务器：" + errorText(error));
                    else showHome();
                });
            }
        }).start();
    }

    private void refreshBootstrapSync() throws Exception {
        JSONObject result = request("GET", "/api/bootstrap", null, true);
        JSONArray jobList = result.optJSONArray("jobs");
        if (jobList != null) {
            jobs = jobList;
            prefs.edit().putString(K_JOBS, jobList.toString()).apply();
        }
        JSONObject user = result.optJSONObject("user");
        if (user != null) {
            prefs.edit()
                    .putString(K_NAME, user.optString("name", ""))
                    .putString(K_ID, user.optString("id", ""))
                    .putBoolean(K_IS_ADMIN, user.optBoolean("isAdmin", false))
                    .apply();
        }
    }

    private JSONObject request(String method, String path, JSONObject body, boolean auth) throws Exception {
        if (sslContext == null) throw new Exception("证书未初始化");
        HttpsURLConnection conn = (HttpsURLConnection) new URL(
                "https://" + serverIp + ":8443" + path).openConnection();
        conn.setSSLSocketFactory(sslContext.getSocketFactory());
        conn.setConnectTimeout(10000);
        conn.setReadTimeout(15000);
        conn.setRequestMethod(method);
        conn.setRequestProperty("Accept", "application/json");
        if (auth) {
            conn.setRequestProperty("Authorization", "Bearer " + prefs.getString(K_TOKEN, ""));
        }
        if (body != null) {
            byte[] data = body.toString().getBytes(StandardCharsets.UTF_8);
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            conn.setFixedLengthStreamingMode(data.length);
            try (OutputStream output = conn.getOutputStream()) {
                output.write(data);
            }
        }
        int status = conn.getResponseCode();
        InputStream input = status >= 400 ? conn.getErrorStream() : conn.getInputStream();
        String text = input == null ? "" : new String(readAll(input), StandardCharsets.UTF_8);
        conn.disconnect();
        JSONObject json = text.isEmpty() ? new JSONObject() : new JSONObject(text);
        if (status >= 400) {
            String message = "请求失败（" + status + "）";
            String code = "";
            JSONObject detail = json.optJSONObject("detail");
            if (detail != null) {
                message = detail.optString("message", message);
                code = detail.optString("code", "");
            }
            throw new ApiException(status, message, code);
        }
        return json;
    }

    private byte[] readAll(InputStream input) throws Exception {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int read;
        while ((read = input.read(buffer)) != -1) {
            output.write(buffer, 0, read);
        }
        return output.toByteArray();
    }

    private static class ApiException extends Exception {
        final int status;
        final String code;

        ApiException(int status, String message, String code) {
            super(message);
            this.status = status;
            this.code = code;
        }
    }
}
