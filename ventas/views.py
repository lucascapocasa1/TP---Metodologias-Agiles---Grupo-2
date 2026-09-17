from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Producto, Categoria
from django.db.models import Q
@login_required
def pantalla_cobro(request):
     """
     Pantalla de cobro (POS). En este Sprint 1 es solo la cáscara protegida
     por login: el flujo real de "escanear código → vuela al carrito",
     el vuelto rápido con billetes y el cierre de caja son de sprints
     siguientes.
     """
     return render(request, "ventas/pantalla_cobro.html")
 # ========== LISTA DE PRODUCTOS ==========
@login_required
def lista_productos(request):
     busqueda = request.GET.get('buscar', '')
     if busqueda:
         productos = Producto.objects.filter(
             Q(nombre__icontains=busqueda) |
             Q(descripcion__icontains=busqueda)
         )
     else:
         productos = Producto.objects.all()
     
     return render(request, 'ventas/lista_productos.html', {
         'productos': productos,
         'busqueda': busqueda
     })
 # ========== AGREGAR PRODUCTO (con opción de categoría nueva) ==========
@login_required
def agregar_producto(request):
     if request.method == 'POST':
         nombre = request.POST.get('nombre')
         descripcion = request.POST.get('descripcion', '')
         precio = request.POST.get('precio')
         stock = request.POST.get('stock')
         categoria_id = request.POST.get('categoria')
         nueva_categoria = request.POST.get('nueva_categoria', '')
         
         # Si escribieron categoría nueva, la creamos
         if nueva_categoria:
             categoria = Categoria.objects.create(nombre=nueva_categoria)
         else:
             categoria = get_object_or_404(Categoria, id=categoria_id)
         
         Producto.objects.create(
             nombre=nombre,
             descripcion=descripcion,
             precio=precio,
             stock=stock,
             categoria=categoria
         )
         return redirect('ventas:lista_productos')
     
     categorias = Categoria.objects.all()
     return render(request, 'ventas/agregar_producto.html', {
         'categorias': categorias
     })







