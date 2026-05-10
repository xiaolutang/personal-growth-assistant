import 'dart:async';

/// 通用防抖工具类
///
/// 用于搜索输入等高频触发场景，在指定延迟内只执行最后一次调用。
/// 典型用法：配合 [TextEditingController] 的 listener 使用。
///
/// ```dart
/// final debouncer = Debouncer();
/// controller.addListener(() {
///   debouncer.run(() => performSearch(controller.text));
/// });
/// ```
///
/// 使用完毕后必须调用 [dispose] 以取消未完成的 Timer，防止内存泄漏。
class Debouncer {
  Debouncer({Duration delay = const Duration(milliseconds: 300)})
      : _delay = delay;

  final Duration _delay;
  Timer? _timer;

  /// 当前是否有一个待执行的防抖任务。
  bool get isActive => _timer?.isActive ?? false;

  /// 延迟执行 [action]。
  ///
  /// 如果在 [_delay] 时间内再次调用，会取消上一次未执行的 Timer，
  /// 仅保留最后一次 [action]。
  void run(void Function() action) {
    _timer?.cancel();
    _timer = Timer(_delay, () {
      _timer = null;
      action();
    });
  }

  /// 立即执行 [action]，取消当前未执行的防抖任务。
  ///
  /// 适用于清空搜索等需要即时响应的场景。
  void immediateRun(void Function() action) {
    _timer?.cancel();
    _timer = null;
    action();
  }

  /// 取消未完成的 Timer，释放资源。
  ///
  /// 调用后不应再使用此实例。通常在 State.dispose() 中调用。
  void dispose() {
    _timer?.cancel();
    _timer = null;
  }
}
