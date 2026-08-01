"""MIDI 后处理：让任意 MIDI 变成"真人十指可弹"的钢琴谱。

- 左右手分轨 (C4=60 分界)
- 每手最多 5 音同时、跨度 ≤12 半音
- 每秒最多 14 音、相邻大跳 ≤24 半音
- 长音符 → CC64 踏板事件
"""

import pretty_midi
import numpy as np


def analyze_issues(notes, label=""):
    """返回可读性约束问题列表，空列表表示可弹"""
    if not notes:
        return ["无音符"]
    issues = []
    times = np.linspace(notes[0]["start"], notes[-1]["end"], 500)
    max_poly = 0
    for t in times:
        active = sum(1 for n in notes if n["start"] <= t < n["end"])
        max_poly = max(max_poly, active)
    if max_poly > 5:
        issues.append(f"同时{max_poly}音")
    onsets = [n["start"] for n in notes]
    max_nps = 0
    for t in onsets:
        cnt = sum(1 for o in onsets if t <= o < t + 1.0)
        max_nps = max(max_nps, cnt)
    if max_nps > 14:
        issues.append(f"密度{max_nps}/s")
    max_span = 0
    for t in times:
        ps = [n["pitch"] for n in notes if n["start"] <= t < n["end"]]
        if len(ps) >= 2:
            max_span = max(max_span, max(ps) - min(ps))
    if max_span > 12:
        issues.append(f"跨度{max_span}")
    max_leap = 0
    for i in range(1, min(len(notes), 500)):
        max_leap = max(max_leap, abs(notes[i]["pitch"] - notes[i - 1]["pitch"]))
    if max_leap > 24:
        issues.append(f"大跳{max_leap}")
    return issues


def enforce_one_hand(notes, max_hand=5, hand_span=12, max_nps=14, max_leap=24):
    """对单手的音符列表施加十指可弹约束"""
    if not notes:
        return []
    notes = sorted(notes, key=lambda n: (n["start"], -n["pitch"]))

    keep = [True] * len(notes)
    for i in range(len(notes)):
        t = notes[i]["start"]
        window = [j for j in range(len(notes)) if t <= notes[j]["start"] < t + 1.0]
        if len(window) > max_nps:
            pairs = [(j, notes[j]["pitch"]) for j in window]
            pairs.sort(key=lambda x: -x[1])
            for j, _ in pairs[max_nps:]:
                keep[j] = False
    notes = [n for i, n in enumerate(notes) if keep[i]]

    if not notes:
        return []

    removed = set()
    events = []
    for i, n in enumerate(notes):
        events.append((n["start"], 1, i, n["pitch"]))
        events.append((n["end"], 0, i, n["pitch"]))
    events.sort(key=lambda e: (e[0], e[1]))

    active_set = {}
    for _time, etype, idx, pitch in events:
        if etype == 0:
            active_set.pop(idx, None)
        else:
            active_set[idx] = pitch
            if len(active_set) > max_hand:
                lowest_idx = min(active_set, key=lambda i: active_set[i])
                removed.add(lowest_idx)
                del active_set[lowest_idx]
            if len(active_set) >= 2:
                pitches_in_use = list(active_set.values())
                while max(pitches_in_use) - min(pitches_in_use) > hand_span:
                    mean_p = np.mean(pitches_in_use)
                    far_idx = max(active_set, key=lambda i: abs(active_set[i] - mean_p))
                    removed.add(far_idx)
                    del active_set[far_idx]
                    pitches_in_use = list(active_set.values())

    result = [n for i, n in enumerate(notes) if i not in removed]

    if len(result) > 1:
        filtered = [result[0]]
        for n in result[1:]:
            prev = filtered[-1]
            leap = abs(n["pitch"] - prev["pitch"])
            gap = n["start"] - prev["start"]
            if leap > max_leap:
                continue
            if gap < 0.1 and leap > 12:
                continue
            filtered.append(n)
        result = filtered

    return result


def _dynamic_note_dur_threshold(notes, fallback=8.0):
    """根据整曲音符时长分布计算动态阈值。

    思路：统计 P90 分位数（90% 音符都不超过的时长），
    阈值 = max(P90 × 1.5, 2.0)，上限 fallback（绝对保护，防转录错误超长音）。
    这样慢曲（长音正常）不会砍音，只有显著偏离曲目正常水平的音才被截断+踏板。
    """
    if not notes:
        return fallback
    durs = np.array([n["end"] - n["start"] for n in notes])
    p90 = float(np.percentile(durs, 90))
    threshold = max(p90 * 1.5, 2.0)
    return min(threshold, fallback)


def process_midi(
    input_path,
    output_path,
    max_note_dur=None,
    split_point=60,
    max_hand=5,
    hand_span=12,
    max_nps=14,
    max_leap=24,
):
    """后处理 MIDI 文件：分轨 + 十指限流 + CC64 踏板。

    Args:
        input_path: 输入 MIDI 文件路径
        output_path: 输出 MIDI 文件路径
        max_note_dur: 最长音符秒数，超过的截断并用 CC64 踏板补延音。
            None=动态阈值（按整曲时长分布自动判断，慢曲保留长音）；数值=固定阈值
        split_point: 左右手分界音高
        max_hand: 每手最大同时发声数
        hand_span: 每手最大跨度（半音）
        max_nps: 每手每秒最大音符密度
        max_leap: 每手最大跳跃间隔（半音）

    Returns:
        dict: 处理统计信息
    """
    mid = pretty_midi.PrettyMIDI(input_path)

    all_notes = []
    for inst in mid.instruments:
        if inst.is_drum:
            continue
        for n in inst.notes:
            all_notes.append({
                "pitch": n.pitch,
                "start": n.start,
                "end": n.end,
                "velocity": n.velocity,
            })
    all_notes.sort(key=lambda n: (n["start"], -n["pitch"]))

    left_raw = [n for n in all_notes if n["pitch"] < split_point]
    right_raw = [n for n in all_notes if n["pitch"] >= split_point]

    left = enforce_one_hand(left_raw, max_hand, hand_span, max_nps, max_leap)
    right = enforce_one_hand(right_raw, max_hand, hand_span, max_nps, max_leap)

    # 动态阈值：None 时按整曲时长分布自动计算，只截显著异常长音
    if max_note_dur is None:
        note_dur_threshold = _dynamic_note_dur_threshold(all_notes)
    else:
        note_dur_threshold = float(max_note_dur)

    left_out, left_cc = [], []
    right_out, right_cc = [], []

    for src_notes, dst_list, cc_list in [
        (left, left_out, left_cc),
        (right, right_out, right_cc),
    ]:
        for n in src_notes:
            dur = n["end"] - n["start"]
            if dur > note_dur_threshold:
                new_end = n["start"] + note_dur_threshold
                dst_list.append({**n, "end": new_end})
                cc_list.append({"t": new_end, "v": 127})
                cc_list.append({"t": n["end"], "v": 0})
            else:
                dst_list.append(n)

    all_cc = sorted(left_cc + right_cc, key=lambda c: c["t"])
    opt = []
    for c in all_cc:
        if opt and opt[-1]["v"] == c["v"] and abs(opt[-1]["t"] - c["t"]) < 0.01:
            continue
        opt.append(c)

    out = pretty_midi.PrettyMIDI()
    for name, notes_out in [("Right Hand", right_out), ("Left Hand", left_out)]:
        inst = pretty_midi.Instrument(program=0, name=name)
        for n in notes_out:
            inst.notes.append(pretty_midi.Note(
                velocity=int(n["velocity"]),
                pitch=int(n["pitch"]),
                start=n["start"],
                end=n["end"],
            ))
        # CC64 踏板只加右手轨，避免双轨重复事件导致延音混乱
        if name == "Right Hand":
            for c in opt:
                inst.control_changes.append(
                    pretty_midi.ControlChange(number=64, value=c["v"], time=c["t"])
                )
        out.instruments.append(inst)

    out.write(output_path)

    return {
        "input_notes": len(all_notes),
        "left_notes": len(left_out),
        "right_notes": len(right_out),
        "total_notes": len(left_out) + len(right_out),
        "cc64_events": len(opt),
    }
