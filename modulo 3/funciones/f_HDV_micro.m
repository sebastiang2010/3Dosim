function [Volumen] =f_HDV_micro(D,Phantom,organo,t_voxel,nfig,i)

%claramente esto tiene que ser un case
         if organo==30;txt='Tejido Blando';end
         if organo==50;txt='Pulmon';end
         if organo==80;txt='Hueso';end
         if organo==90;txt='Higado sano';c='b';end    
         if organo>=100;txt='Tumor';c='r';end
         if organo==99;txt='Pretumor';c='g';end
         %if organo==-1;txt='Hepatic Arteria';c='g';end  
         
         if i==1;c='r';end 
         if i==2;c='b';end
         if i==3;c='c';end
         if i==4;c='k';end
         if i==5;c='y';end
         
      
         
         ind=Phantom==organo;
         D=D(ind);
         n=numel(D); %numero de pixel
         
         Volumen=n*prod(t_voxel); %cm
         %if i==1;lengend('')
                 
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
         h_title=title(['Cumulative Dose Volume Histogram Organo : ',txt]);
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


   txt2={'hepatic arteria','bile duct','portal vein','parenquima','central vein'};
   legend(txt2)
end 