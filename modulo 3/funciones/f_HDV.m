function [Volumen,Dx] =f_HDV(D,Phantom,organo,t_voxel,nfig,Dx)

%claramente esto tiene que ser un case
%if organo==30;txt='Tejido Blando';end
%if organo==50;txt='Pulmon';end
%if organo==80;txt='Hueso';end
%if organo==90;txt='Higado sano';c='b';end
%if organo>=100;txt='Tumor';c='r';end
%if organo==99;txt='Pretumor';c='g';end
%if organo==-1;txt='Hepatic Arteria';c='g';end

        % --- Tu bloque original, añadiendo 'campo' para la estructura ---
        if organo==30
            txt='Tejido Blando'; campo='TejidoBlando'; c='k';
        end
        if organo==50
            txt='Pulmon';        campo='Pulmon';       c='k';
        end
        if organo==80
            txt='Hueso';         campo='Hueso';        c='k';
        end
        if organo==90
            txt='Higado sano';   campo='Higado';       c='b';
        end
        if organo>=100
            txt='Tumor';         campo='tumor';        c='r';   % Si hay varios, se pisan; puedes usar ['tumor' num2str(organo)]
        end
        if organo==99
            txt='Pretumor';      campo='pretumor';     c='g';
        end


ind=Phantom==organo;
D=D(ind);
n=numel(D); %numero de pixel

Volumen=n*prod(t_voxel); %cm


%%%%%histograma dosis Volumen
Dmax=max(D);
if Dmax==0;return;end
delta=Dmax/1000;
i=1;
a=zeros(1001,1);
for d=0:delta:Dmax
    a(i,1)=sum(D>=d)*100/n;
    i=i+1;
end

d=0:delta:Dmax;
figure(nfig)
h_plot=plot(d,a);
set(h_plot,'LineWidth',2);
set(h_plot,'Color',c)
set(gca,'YLim',[0 200]);

h_x=xlabel('Dose (Gy)');
h_y=ylabel('Volume (%)');
%h_title=title(['Cumulative Dose Volume Histogram Organo : ',txt]);
h_title=title('Cumulative Dose Volume Histogram');
set(h_title,'FontWeight','bold');
set(h_x,'FontWeight','bold');
set(h_y,'FontWeight','bold');
set(gca,'XGrid','on');
set(gca,'YGrid','on');
set(gca,'YScale','log');
%set(gca,'XScale','log');
set(gca,'NextPlot','add');
%set(gca,'XLim',[0.01 Dmax+Dmax*0.1]);

%      Dmean=mean(D);
%      sigma=std(D);
%      Dmin=min(D);



txt={'Higado','tumor','pretumor'};
legend(txt)

%% 
 
 Dx.(campo) = f_Dx_DVH(d, a);


end

