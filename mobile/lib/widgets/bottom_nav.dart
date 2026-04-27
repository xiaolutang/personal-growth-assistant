import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class BottomNavShell extends StatefulWidget {
  final Widget child;

  const BottomNavShell({super.key, required this.child});

  @override
  State<BottomNavShell> createState() => _BottomNavShellState();
}

class _BottomNavShellState extends State<BottomNavShell> {
  void _showMoreMenu() {
    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Wrap(
          children: [
            ListTile(
              leading: const Icon(Icons.bar_chart),
              title: const Text('回顾'),
              onTap: () {
                Navigator.pop(context);
                this.context.go('/review');
              },
            ),
            ListTile(
              leading: const Icon(Icons.flag),
              title: const Text('目标'),
              onTap: () {
                Navigator.pop(context);
                this.context.go('/goals');
              },
            ),
            ListTile(
              leading: const Icon(Icons.lightbulb),
              title: const Text('灵感'),
              onTap: () {
                Navigator.pop(context);
                this.context.go('/inbox');
              },
            ),
            ListTile(
              leading: const Icon(Icons.explore),
              title: const Text('探索'),
              onTap: () {
                Navigator.pop(context);
                this.context.go('/explore');
              },
            ),
          ],
        ),
      ),
    );
  }

  int _currentIndex() {
    final location = GoRouterState.of(context).uri.path;
    if (location.startsWith('/chat')) return 1;
    if (location.startsWith('/tasks')) return 2;
    if (location.startsWith('/notes')) return 3;
    return 0; // default: today
  }

  bool _isOnMoreRoute() {
    final location = GoRouterState.of(context).uri.path;
    return location.startsWith('/review') ||
        location.startsWith('/goals') ||
        location.startsWith('/inbox') ||
        location.startsWith('/explore');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: widget.child,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _isOnMoreRoute() ? 4 : _currentIndex(),
        onDestinationSelected: (index) {
          if (index == 4) {
            _showMoreMenu();
            return;
          }
          switch (index) {
            case 0:
              context.go('/');
            case 1:
              context.go('/chat');
            case 2:
              context.go('/tasks');
            case 3:
              context.go('/notes');
          }
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home),
            label: '今天',
          ),
          NavigationDestination(
            icon: Icon(Icons.chat_bubble_outline),
            selectedIcon: Icon(Icons.chat_bubble),
            label: '日知',
          ),
          NavigationDestination(
            icon: Icon(Icons.check_circle_outline),
            selectedIcon: Icon(Icons.check_circle),
            label: '任务',
          ),
          NavigationDestination(
            icon: Icon(Icons.note_outlined),
            selectedIcon: Icon(Icons.note),
            label: '笔记',
          ),
          NavigationDestination(
            icon: Icon(Icons.more_horiz),
            selectedIcon: Icon(Icons.more_horiz),
            label: '更多',
          ),
        ],
      ),
    );
  }
}
