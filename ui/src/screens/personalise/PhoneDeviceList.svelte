<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- GENERATED from Claude Design's `Phone Device List.dc.html` (design/source/14-first-use)
     by `tools/design/gen_personalise.py`: Spotify's device list, the player in it. -->
<script>
  let { device = 'Living Room' } = $props();
  const V = $derived({ device });
</script>

<div style="width:100%;height:100%;min-height:180px;box-sizing:border-box;border-radius:18px;overflow:hidden;background:#121212;color:#ffffff;font-family:-apple-system,'SF Pro Text','Helvetica Neue',Helvetica,sans-serif;display:flex;flex-direction:column;gap:12px;padding:10px 16px 0;border:1px solid rgba(255,255,255,0.08);">
  <div style="align-self:center;width:36px;height:4px;border-radius:2px;background:rgba(255,255,255,0.28);flex-shrink:0;"></div>
  <div style="font-size:15px;font-weight:700;text-align:center;flex-shrink:0;">Connect to a device</div>
  <div style="display:flex;align-items:center;gap:12px;flex-shrink:0;">
    <span style="width:28px;height:28px;display:flex;align-items:center;justify-content:center;flex-shrink:0;"><span style="width:13px;height:21px;border:2px solid #7ed6bc;border-radius:3px;box-sizing:border-box;display:block;"></span></span>
    <span style="flex:1;min-width:0;"><span style="display:block;font-size:14px;font-weight:600;color:#7ed6bc;">This phone</span><span style="display:block;font-size:12px;color:#a7a7a7;margin-top:1px;">Current device</span></span>
  </div>
  <div style="font-size:13px;font-weight:700;color:#e9e9e9;flex-shrink:0;">Select a device</div>
  <div style="display:flex;flex-direction:column;gap:2px;margin:0 -10px;">
    <div style="display:flex;align-items:center;gap:12px;padding:8px 10px;border-radius:10px;background:rgba(255,255,255,0.09);flex-shrink:0;">
      <span style="width:28px;height:28px;display:flex;align-items:center;justify-content:center;flex-shrink:0;"><span style="width:17px;height:22px;border:2px solid #e6e6e6;border-radius:4px;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;justify-content:space-evenly;"><span style="width:3px;height:3px;border-radius:50%;background:#e6e6e6;display:block;"></span><span style="width:8px;height:8px;border-radius:50%;border:2px solid #e6e6e6;box-sizing:border-box;display:block;"></span></span></span>
      <span style="flex:1;min-width:0;"><span style="display:block;font-size:14px;font-weight:600;">{V.device}</span><span style="display:block;font-size:12px;color:#a7a7a7;margin-top:1px;">Spotify Connect</span></span>
    </div>
    <div style="display:flex;align-items:center;gap:12px;padding:8px 10px;border-radius:10px;flex-shrink:0;">
      <span style="width:28px;height:28px;display:flex;align-items:center;justify-content:center;flex-shrink:0;"><span style="width:17px;height:22px;border:2px solid #cfcfcf;border-radius:4px;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;justify-content:space-evenly;"><span style="width:3px;height:3px;border-radius:50%;background:#cfcfcf;display:block;"></span><span style="width:8px;height:8px;border-radius:50%;border:2px solid #cfcfcf;box-sizing:border-box;display:block;"></span></span></span>
      <span style="flex:1;min-width:0;"><span style="display:block;font-size:14px;font-weight:600;">Kitchen</span><span style="display:block;font-size:12px;color:#a7a7a7;margin-top:1px;">Smart speaker</span></span>
    </div>
    <div style="display:flex;align-items:center;gap:12px;padding:8px 10px;border-radius:10px;flex-shrink:0;">
      <span style="width:28px;height:28px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1px;flex-shrink:0;"><span style="width:20px;height:13px;border:2px solid #cfcfcf;border-radius:2px;box-sizing:border-box;display:block;"></span><span style="width:26px;height:2px;border-radius:1px;background:#cfcfcf;display:block;"></span></span>
      <span style="flex:1;min-width:0;"><span style="display:block;font-size:14px;font-weight:600;">MacBook Pro</span><span style="display:block;font-size:12px;color:#a7a7a7;margin-top:1px;">Computer</span></span>
    </div>
    <div style="display:flex;align-items:center;gap:12px;padding:8px 10px;border-radius:10px;flex-shrink:0;">
      <span style="width:28px;height:28px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;flex-shrink:0;"><span style="width:24px;height:15px;border:2px solid #cfcfcf;border-radius:2px;box-sizing:border-box;display:block;"></span><span style="width:10px;height:2px;background:#cfcfcf;display:block;"></span></span>
      <span style="flex:1;min-width:0;"><span style="display:block;font-size:14px;font-weight:600;">Bedroom TV</span><span style="display:block;font-size:12px;color:#a7a7a7;margin-top:1px;">TV</span></span>
    </div>
  </div>
</div>
