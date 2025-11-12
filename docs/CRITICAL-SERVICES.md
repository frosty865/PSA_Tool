# Critical Services Guide

## Service Criticality Levels

### 🔴 **CRITICAL** - System cannot function without these

#### 1. VOFC-Ollama
**Status:** 🔴 CRITICAL  
**Purpose:** Core AI model server  
**Why Critical:**
- All AI processing depends on Ollama
- VOFC-Processor requires it to extract vulnerabilities/OFCs
- VOFC-Flask uses it for API endpoints
- Without it, no document processing can occur

**Impact if Down:**
- ❌ No document processing
- ❌ No AI extraction
- ❌ API endpoints fail
- ❌ Frontend cannot function

**Recovery Priority:** **HIGHEST** - Fix immediately

---

#### 2. VOFC-Flask
**Status:** 🔴 CRITICAL  
**Purpose:** REST API server for frontend  
**Why Critical:**
- Frontend communicates with Flask API
- All user interactions go through Flask
- File uploads, processing requests, data retrieval
- Without it, frontend cannot function

**Impact if Down:**
- ❌ Frontend cannot connect
- ❌ No file uploads
- ❌ No API responses
- ❌ Users cannot interact with system

**Recovery Priority:** **HIGHEST** - Fix immediately

**Dependencies:** VOFC-Ollama (for AI processing)

---

### 🟡 **IMPORTANT** - Core functionality affected

#### 3. VOFC-Processor
**Status:** 🟡 IMPORTANT  
**Purpose:** Automated PDF processing service  
**Why Important:**
- Automatically processes PDFs from incoming directory
- Extracts vulnerabilities and OFCs
- Uploads to Supabase
- Without it, manual processing required

**Impact if Down:**
- ⚠️ PDFs accumulate in incoming directory
- ⚠️ Manual processing required
- ⚠️ No automatic extraction
- ✅ System still functions (manual processing possible)

**Recovery Priority:** **HIGH** - Fix within hours

**Dependencies:** VOFC-Ollama

**Workaround:** Manual processing via Flask API or direct script execution

---

### 🟢 **OPTIONAL** - Nice to have, not required

#### 4. VOFC-Tunnel
**Status:** 🟢 OPTIONAL  
**Purpose:** Cloudflare tunnel for external access  
**Why Optional:**
- Only needed for external access
- Local access works without it
- Can use VPN or other methods

**Impact if Down:**
- ⚠️ No external access
- ✅ Local access still works
- ✅ System fully functional locally

**Recovery Priority:** **MEDIUM** - Fix when external access needed

**Dependencies:** VOFC-Flask

**Workaround:** Use VPN, port forwarding, or direct IP access

---

#### 5. VOFC-ModelManager
**Status:** 🟢 OPTIONAL  
**Purpose:** Autonomous model monitoring and retraining  
**Why Optional:**
- Model retraining can be done manually
- System works with existing models
- Not required for day-to-day operations

**Impact if Down:**
- ⚠️ No automatic model monitoring
- ⚠️ No automatic retraining
- ✅ System continues to function
- ✅ Manual retraining still possible

**Recovery Priority:** **LOW** - Fix when convenient

**Dependencies:** VOFC-Ollama

**Workaround:** Manual retraining via scripts or API

---

#### 6. VOFC-AutoRetrain
**Status:** 🟢 OPTIONAL  
**Purpose:** Scheduled automatic retraining jobs  
**Why Optional:**
- Retraining can be triggered manually
- Not required for processing documents
- Scheduled job, not real-time

**Impact if Down:**
- ⚠️ No scheduled retraining
- ✅ Manual retraining still works
- ✅ System fully functional

**Recovery Priority:** **LOW** - Fix when convenient

**Dependencies:** VOFC-Ollama

**Workaround:** Manual retraining via scripts

---

## Criticality Summary

| Service | Criticality | Required For | Recovery Priority |
|---------|------------|--------------|-------------------|
| **VOFC-Ollama** | 🔴 CRITICAL | All AI processing | HIGHEST |
| **VOFC-Flask** | 🔴 CRITICAL | Frontend/API access | HIGHEST |
| **VOFC-Processor** | 🟡 IMPORTANT | Automated processing | HIGH |
| **VOFC-Tunnel** | 🟢 OPTIONAL | External access | MEDIUM |
| **VOFC-ModelManager** | 🟢 OPTIONAL | Auto model management | LOW |
| **VOFC-AutoRetrain** | 🟢 OPTIONAL | Scheduled retraining | LOW |

## Minimum Viable System

For basic functionality, you need:

1. ✅ **VOFC-Ollama** - AI model server
2. ✅ **VOFC-Flask** - API server

With just these two services:
- ✅ Frontend can connect
- ✅ Documents can be processed (via API)
- ✅ Users can interact with system
- ⚠️ No automatic processing (manual via API)

## Recommended Production Setup

For full automated operation:

1. ✅ **VOFC-Ollama** - AI model server
2. ✅ **VOFC-Flask** - API server
3. ✅ **VOFC-Processor** - Automated processing
4. ✅ **VOFC-Tunnel** - External access (if needed)

## Monitoring Priorities

### High Priority Monitoring
- **VOFC-Ollama** - Check every 5 minutes
- **VOFC-Flask** - Check every 5 minutes
- **VOFC-Processor** - Check every 15 minutes

### Medium Priority Monitoring
- **VOFC-Tunnel** - Check every hour (if external access needed)

### Low Priority Monitoring
- **VOFC-ModelManager** - Check daily
- **VOFC-AutoRetrain** - Check daily

## Startup Order (Criticality-Based)

1. **VOFC-Ollama** (CRITICAL - Start first)
2. **VOFC-Flask** (CRITICAL - Depends on Ollama)
3. **VOFC-Processor** (IMPORTANT - Depends on Ollama)
4. **VOFC-Tunnel** (OPTIONAL - Depends on Flask)
5. **VOFC-ModelManager** (OPTIONAL - Depends on Ollama)
6. **VOFC-AutoRetrain** (OPTIONAL - Depends on Ollama)

## Recovery Procedures

### If VOFC-Ollama is Down
1. Check Ollama service status: `nssm status VOFC-Ollama`
2. Check Ollama logs: `Get-Content C:\Tools\Ollama\Data\logs\ollama.log -Tail 50`
3. Restart service: `nssm restart VOFC-Ollama`
4. Verify Ollama API: `curl http://localhost:11434/api/tags`
5. If still down, check Ollama installation and model availability

### If VOFC-Flask is Down
1. Check Flask service status: `nssm status VOFC-Flask`
2. Check Flask logs: `Get-Content C:\Tools\Ollama\Data\logs\flask_*.log -Tail 50`
3. Verify Ollama is running (dependency)
4. Restart service: `nssm restart VOFC-Flask`
5. Test API: `curl http://localhost:8080/api/system/health`
6. If still down, check Python dependencies and configuration

### If VOFC-Processor is Down
1. Check Processor service status: `nssm status VOFC-Processor`
2. Check Processor logs: `Get-Content C:\Tools\Ollama\Data\logs\vofc_processor_*.log -Tail 50`
3. Verify Ollama is running (dependency)
4. Restart service: `nssm restart VOFC-Processor`
5. Test by dropping a PDF in incoming directory
6. **Workaround:** Process documents manually via Flask API

## Health Check Script

```powershell
# Quick health check for critical services
$critical = @("VOFC-Ollama", "VOFC-Flask")
$important = @("VOFC-Processor")

Write-Host "Critical Services:" -ForegroundColor Red
foreach ($svc in $critical) {
    $status = nssm status $svc 2>&1
    $color = if ($status -eq "SERVICE_RUNNING") { "Green" } else { "Red" }
    Write-Host "  $svc : $status" -ForegroundColor $color
}

Write-Host "`nImportant Services:" -ForegroundColor Yellow
foreach ($svc in $important) {
    $status = nssm status $svc 2>&1
    $color = if ($status -eq "SERVICE_RUNNING") { "Green" } else { "Yellow" }
    Write-Host "  $svc : $status" -ForegroundColor $color
}
```

## Service Dependencies Chart

```
VOFC-Ollama (CRITICAL)
    ├── VOFC-Flask (CRITICAL)
    │   └── VOFC-Tunnel (OPTIONAL)
    ├── VOFC-Processor (IMPORTANT)
    ├── VOFC-ModelManager (OPTIONAL)
    └── VOFC-AutoRetrain (OPTIONAL)
```

## Recommendations

1. **Always monitor critical services** - Set up alerts for VOFC-Ollama and VOFC-Flask
2. **Test recovery procedures** - Know how to restart critical services quickly
3. **Have backups** - Keep service configurations and scripts backed up
4. **Document workarounds** - Know manual alternatives for optional services
5. **Prioritize uptime** - Focus on keeping critical services running

