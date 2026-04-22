import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

void main() {
  runApp(const ProviderScope(child: GrowthApp()));
}

class GrowthApp extends StatelessWidget {
  const GrowthApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '个人成长助手',
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF6366F1),
        useMaterial3: true,
      ),
      home: const Scaffold(
        body: Center(child: Text('个人成长助手')),
      ),
    );
  }
}
