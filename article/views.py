#from myblog import article
#from _typeshed import SupportsItemAccess
from typing import ContextManager
from django.shortcuts import render,redirect
from django.http import HttpResponse
from .forms import ArticlePostForm
from django.contrib.auth.models import User
from django.template.response import ContentNotRenderedError
from .models import ArticlePost
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from comment.models import Comment
import markdown
from .models import ArticleColumn
from comment.forms import CommentForm

def article_list(request):
    search = request.GET.get('search')
    order = request.GET.get('order')
    #用户搜索逻辑
    if search:
        if  order == 'total_views':
            #用Q对象，进行联合搜索
            article_list = ArticlePost.objects.filter(
                Q(title_icontains=search) |
                Q(body_icontains=search)
            ).order_by('-total_views')
        else:
            article_list = ArticlePost.objects.filter(
                Q(title__icontains=search) |
                Q(body__icontains=search)
            )
    else:
        # 将 search 参数重置为空
        search = ''
        if order == 'total_views':
            article_list = ArticlePost.objects.all().order_by('-total_views')
        else:
            article_list = ArticlePost.objects.all()
       

    # 每页显示 3篇文章
    paginator = Paginator(article_list, 3)
    # 获取 url 中的页码
    page = request.GET.get('page')
    # 将导航对象相应的页码内容返回给 articles
    articles = paginator.get_page(page)

    context = { 'articles': articles,'order':order ,'search': search}
    return render(request, 'article/list.html', context)
#文章详情
def article_detail(request, id):
    # 取出相应的文章
    article = ArticlePost.objects.get(id=id)

    # 取出文章评论
    comments = Comment.objects.filter(article=id)
    # 浏览量 +1
    article.total_views += 1
    article.save(update_fields=['total_views'])

    # 修改 Markdown 语法渲染
    md = markdown.Markdown(
        extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc',
        ]
    )
    article.body = md.convert(article.body)
    comment_form = CommentForm()
    # 需要传递给模板的对象
    context = { 'article': article, 'toc':md.toc,'comments':comments,'comment_form':comment_form ,}
    # 载入模板，并返回context对象
    return render(request, 'article/detail.html', context)

#写文章
@login_required(login_url='/userprofile/login/')
def article_create(request):    
    # 判断用户是否提交数据
    if request.method == "POST":
        # 将提交的数据赋值到表单实例中
        article_post_form = ArticlePostForm(request.POST,request.FILES)
        #判断是否满足
        if article_post_form.is_valid():
            new_article = article_post_form.save(commit=False)
            new_article.author = User.objects.get(id=request.user.id)
           # new_article.author = User.objects.get(id=1)  
            
            if request.POST['column'] != 'none':
                new_article.column = ArticleColumn.objects.get(id=request.POST['column'])
            new_article.save()

            article_post_form.save_m2m()

            return redirect("article:article_list")
            
        else:
            return HttpResponse("表单内容有误，请重新填写")
    else:
        article_post_form = ArticlePostForm()
        columns = ArticleColumn.objects.all()
        context = {'article_post_form':article_post_form,'columns': columns  }

        return render(request,'article/create.html',context)
    

#删文章
def article_delete(request, id):
    # 根据 id 获取需要删除的文章
    article = ArticlePost.objects.get(id=id)
    # 调用.delete()方法删除文章
    article.delete()
    # 完成删除后返回文章列表
    return redirect("article:article_list")

# 安全删除文章
def article_safe_delete(request, id):
    if request.method == 'POST':
        article = ArticlePost.objects.get(id=id)
        article.delete()
        return redirect("article:article_list")
    else:
        return HttpResponse("仅允许post请求")

# 更新文章
@login_required(login_url='/userprofile/login/')
def article_update(request,id):
    article = ArticlePost.objects.get(id=id)
        # 过滤非作者的用户
    if request.user != article.author:
        return HttpResponse("抱歉，你无权修改这篇文章。")
    if request.method == "POST":
        article_post_form = ArticlePostForm(data=request.POST)
        if article_post_form.is_valid():
            article.title = request.POST['title']
            article.body = request.POST['body']

            if request.POST['column'] != 'none':
                article.column = ArticleColumn.objects.get(id=request.POST['column'])
            else:
                article.column = None

            #文章标题图部分添加代码--
            if request.FILES.get('avatar'):
                article.avatar = request.FILES.get('avatar')
                
            article.tags.set(*request.POST.get('tags').split(','), clear=True)
            #------
            article.save()
            return redirect("article:article_detail", id=id)
        else:
            return HttpResponse("表单内容有误，请从新填写.")

    else:
        article_post_form = ArticlePostForm()
        columns = ArticleColumn.objects.all()
        context = { 'article': article, 'article_post_form': article_post_form ,'column':columns, 'tags': ','.join([x for x in article.tags.names()]),}
        return render(request, 'article/update.html', context)
