-- cam-switch.lua: 432 Bleu two-phone auto-switcher for OBS (Tools -> Scripts -> +).
--
-- * Alternates between the two iPhone scenes, holding each shot for a random
--   number of seconds between "Shortest shot" and "Longest shot".
-- * If the phone on air drops out, it cuts to the other phone (when that one is up).
-- * Hands off whenever a scene other than the two camera scenes is on air,
--   and while Studio Mode is on.
-- * Clicking a camera scene yourself restarts the shot timer.
-- * Optional hotkey: Settings -> Hotkeys -> "Toggle camera auto-switch".
-- Every action is printed to the Script Log and the OBS log, prefixed [cam-switch.lua].

obs = obslua

local cfg = {
  enabled = false,
  min_s = 20,
  max_s = 40,
  scenes = { "iPhone Cam 1", "iPhone Cam 2" },
  feeds = { "iPhone 1 feed", "iPhone 2 feed" },
}

local DOWN_AFTER = 3          -- seconds a feed must stay down before we cut away from it
local shot_s, target_s = 0, 30
local down_s = { 0, 0 }
local settings_ref = nil
local hotkey_id = obs.OBS_INVALID_HOTKEY_ID
local studio_note = false
local last_scene = nil

-- NO obs_frontend_add_event_callback in this script. The timer runs on OBS's
-- graphics thread holding this script's lock; obs_frontend_set_current_scene
-- waits for the UI thread, and the UI thread's SCENE_CHANGED event would need
-- that same lock -> OBS freezes. That froze OBS on 2026-11-10. Manual cuts are
-- detected by polling the scene name in tick() instead.

local function new_target()
  local lo, hi = cfg.min_s, cfg.max_s
  if hi < lo then lo, hi = hi, lo end
  target_s = math.random(lo, hi)
  shot_s = 0
end

-- A feed counts as up when its media source is playing and has a picture.
local function feed_up(i)
  local src = obs.obs_get_source_by_name(cfg.feeds[i])
  if src == nil then return false end
  local state = obs.obs_source_media_get_state(src)
  local width = obs.obs_source_get_width(src)
  obs.obs_source_release(src)
  return state == obs.OBS_MEDIA_STATE_PLAYING and width > 0
end

-- Name of the scene on air, and its index (1 or 2) if it is a camera scene.
local function on_air()
  local src = obs.obs_frontend_get_current_scene()
  if src == nil then return nil, nil end
  local name = obs.obs_source_get_name(src)
  obs.obs_source_release(src)
  for i, n in ipairs(cfg.scenes) do
    if n == name then return name, i end
  end
  return name, nil
end

local function cut_to(i, why)
  local src = obs.obs_get_source_by_name(cfg.scenes[i])
  if src == nil then
    print("scene not found: " .. cfg.scenes[i])
    return
  end
  obs.obs_frontend_set_current_scene(src)
  obs.obs_source_release(src)
  last_scene = cfg.scenes[i]
  print(string.format("-> %s (%s)", cfg.scenes[i], why))
  new_target()
end

local function tick()
  for i = 1, 2 do
    if feed_up(i) then
      if down_s[i] >= DOWN_AFTER then print("feed " .. i .. " is back") end
      down_s[i] = 0
    else
      down_s[i] = down_s[i] + 1
      if down_s[i] == DOWN_AFTER then print("feed " .. i .. " is down") end
    end
  end

  if not cfg.enabled then return end

  if obs.obs_frontend_preview_program_mode_active() then
    if not studio_note then
      print("Studio Mode is on: auto-switch is standing by")
      studio_note = true
    end
    return
  end
  studio_note = false

  local name, cur = on_air()
  if name ~= last_scene then      -- you cut by hand: restart the shot timer
    last_scene = name
    new_target()
  end
  if cur == nil then return end
  local other = 3 - cur
  shot_s = shot_s + 1

  if down_s[cur] >= DOWN_AFTER then
    if down_s[other] == 0 then cut_to(other, "phone " .. cur .. " dropped") end
    return
  end
  if shot_s >= target_s and down_s[other] == 0 then
    cut_to(other, "timer, " .. shot_s .. " s")
  end
end

local function set_enabled(on, why)
  cfg.enabled = on
  if settings_ref ~= nil then obs.obs_data_set_bool(settings_ref, "enabled", on) end
  new_target()
  print(string.format("auto-switch %s (%s, shots %d-%d s)", on and "ON" or "OFF", why, cfg.min_s, cfg.max_s))
end

function script_description()
  return "<b>432 Bleu camera auto-switch</b><br>" ..
    "Alternates the two iPhone scenes on a random timer and cuts away from a phone that drops. " ..
    "Stays out of the way when any other scene is on air or Studio Mode is on. " ..
    "Hotkey: Settings → Hotkeys → <i>Toggle camera auto-switch</i>."
end

function script_properties()
  local p = obs.obs_properties_create()
  obs.obs_properties_add_bool(p, "enabled", "Auto-switch the cameras")
  obs.obs_properties_add_int(p, "min_s", "Shortest shot (seconds)", 5, 600, 1)
  obs.obs_properties_add_int(p, "max_s", "Longest shot (seconds)", 5, 600, 1)
  obs.obs_properties_add_text(p, "scene1", "Camera 1 scene", obs.OBS_TEXT_DEFAULT)
  obs.obs_properties_add_text(p, "feed1", "Camera 1 feed source", obs.OBS_TEXT_DEFAULT)
  obs.obs_properties_add_text(p, "scene2", "Camera 2 scene", obs.OBS_TEXT_DEFAULT)
  obs.obs_properties_add_text(p, "feed2", "Camera 2 feed source", obs.OBS_TEXT_DEFAULT)
  return p
end

function script_defaults(s)
  obs.obs_data_set_default_bool(s, "enabled", false)
  obs.obs_data_set_default_int(s, "min_s", 20)
  obs.obs_data_set_default_int(s, "max_s", 40)
  obs.obs_data_set_default_string(s, "scene1", "iPhone Cam 1")
  obs.obs_data_set_default_string(s, "feed1", "iPhone 1 feed")
  obs.obs_data_set_default_string(s, "scene2", "iPhone Cam 2")
  obs.obs_data_set_default_string(s, "feed2", "iPhone 2 feed")
end

function script_update(s)
  local was = cfg.enabled
  cfg.enabled = obs.obs_data_get_bool(s, "enabled")
  cfg.min_s = obs.obs_data_get_int(s, "min_s")
  cfg.max_s = obs.obs_data_get_int(s, "max_s")
  cfg.scenes = { obs.obs_data_get_string(s, "scene1"), obs.obs_data_get_string(s, "scene2") }
  cfg.feeds = { obs.obs_data_get_string(s, "feed1"), obs.obs_data_get_string(s, "feed2") }
  if cfg.enabled ~= was then set_enabled(cfg.enabled, "settings") end
end

function script_load(s)
  settings_ref = s
  math.randomseed(os.time())
  new_target()
  hotkey_id = obs.obs_hotkey_register_frontend("cam_switch.toggle", "Toggle camera auto-switch",
    function(pressed) if pressed then set_enabled(not cfg.enabled, "hotkey") end end)
  local a = obs.obs_data_get_array(s, "cam_switch.toggle")
  obs.obs_hotkey_load(hotkey_id, a)
  obs.obs_data_array_release(a)
  obs.timer_add(tick, 1000)
  print("loaded; auto-switch is " .. (cfg.enabled and "ON" or "OFF"))
end

function script_save(s)
  local a = obs.obs_hotkey_save(hotkey_id)
  obs.obs_data_set_array(s, "cam_switch.toggle", a)
  obs.obs_data_array_release(a)
end

function script_unload()
  obs.timer_remove(tick)
end
